import { NextRequest, NextResponse } from 'next/server';
import { withRBAC, AuthenticatedRequest } from '@/lib/rbac-middleware';
import { UserListParams } from '@/types/admin';
import { Pool } from 'pg';

async function getUsersHandler(
  request: AuthenticatedRequest
): Promise<NextResponse> {
  try {
    const { searchParams } = new URL(request.url);

    // Parse query parameters
    const params: UserListParams = {
      page: parseInt(searchParams.get('page') || '1'),
      pageSize: Math.min(parseInt(searchParams.get('pageSize') || '20'), 100), // Max 100 per page
      search: searchParams.get('search') || undefined,
      sortBy: (searchParams.get('sortBy') as any) || 'createdAt',
      sortOrder: (searchParams.get('sortOrder') as 'asc' | 'desc') || 'desc',
      role: (searchParams.get('role') as 'admin' | 'user') || undefined,
    };

    // Connect to BetterAuth PostgreSQL database
    const pool = new Pool({
      connectionString:
        process.env.AUTH_DATABASE_URL ||
        'postgresql://postgres:password@localhost:5433/better_auth',
    });

    try {
      // Build query
      let query =
        'SELECT id, email, name, username, role, "emailVerified", "createdAt", "updatedAt" FROM "user"';
      let conditions: string[] = [];
      let values: any[] = [];
      let paramCount = 0;

      // Add search condition
      if (params.search) {
        paramCount++;
        conditions.push(
          `(email ILIKE $${paramCount} OR name ILIKE $${paramCount} OR username ILIKE $${paramCount})`
        );
        values.push(`%${params.search}%`);
      }

      // Add role filter
      if (params.role) {
        paramCount++;
        conditions.push(`role = $${paramCount}`);
        values.push(params.role);
      }

      // Add WHERE clause if conditions exist
      if (conditions.length > 0) {
        query += ' WHERE ' + conditions.join(' AND ');
      }

      // Add ordering - note: lastActivity and documentCount sorting will be done in memory since they come from external API
      let sortColumn: string;
      switch (params.sortBy) {
        case 'createdAt':
          sortColumn = '"createdAt"';
          break;
        case 'email':
          sortColumn = 'email';
          break;
        case 'name':
          sortColumn = 'name';
          break;
        case 'lastActivity':
        case 'documentCount':
          // These will be sorted in memory after fetching stats
          sortColumn = '"createdAt"'; // Default sort for DB query
          break;
        default:
          sortColumn = params.sortBy;
      }

      query += ` ORDER BY ${sortColumn} ${params.sortOrder.toUpperCase()}`;

      // Add pagination
      const offset = (params.page - 1) * params.pageSize;
      paramCount++;
      query += ` LIMIT $${paramCount}`;
      values.push(params.pageSize);

      paramCount++;
      query += ` OFFSET $${paramCount}`;
      values.push(offset);

      // Execute query
      const result = await pool.query(query, values);

      // Get total count
      let countQuery = 'SELECT COUNT(*) FROM "user"';
      let countValues: any[] = [];
      let countParamCount = 0;

      if (params.search) {
        countParamCount++;
        countQuery += ` WHERE (email ILIKE $${countParamCount} OR name ILIKE $${countParamCount} OR username ILIKE $${countParamCount})`;
        countValues.push(`%${params.search}%`);

        if (params.role) {
          countParamCount++;
          countQuery += ` AND role = $${countParamCount}`;
          countValues.push(params.role);
        }
      } else if (params.role) {
        countParamCount++;
        countQuery += ` WHERE role = $${countParamCount}`;
        countValues.push(params.role);
      }

      const countResult = await pool.query(countQuery, countValues);
      const total = parseInt(countResult.rows[0].count);

      // Fetch document statistics for each user from the main API
      const usersWithStats = await Promise.all(
        result.rows.map(async (row) => {
          try {
            // For now, use mock data for document statistics
            // TODO: Replace with actual API call when main API supports user stats endpoint
            let stats = {
              documentCount: Math.floor(Math.random() * 20),
              documentsCompleted: 0,
              documentsPending: 0,
              documentsProcessing: 0,
              documentsFailed: 0,
              lastActivity:
                Math.random() > 0.3
                  ? new Date(
                      Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000
                    )
                  : null,
            };

            stats.documentsCompleted = Math.floor(stats.documentCount * 0.7);
            stats.documentsProcessing = Math.floor(stats.documentCount * 0.2);
            stats.documentsFailed = Math.floor(stats.documentCount * 0.1);
            stats.documentsPending =
              stats.documentCount -
              stats.documentsCompleted -
              stats.documentsProcessing -
              stats.documentsFailed;

            // Uncomment when main API supports user stats endpoint:
            /*
            try {
              const statsResponse = await fetch(
                `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/admin/users/${row.id}/stats`,
                {
                  headers: {
                    Authorization: `Bearer ${process.env.ADMIN_API_TOKEN || ''}`,
                  },
                }
              );

              if (statsResponse.ok) {
                const statsData = await statsResponse.json();
                stats = {
                  documentCount: statsData.total_documents || 0,
                  documentsCompleted: statsData.completed_documents || 0,
                  documentsPending: statsData.pending_documents || 0,
                  documentsProcessing: statsData.processing_documents || 0,
                  documentsFailed: statsData.failed_documents || 0,
                  lastActivity: statsData.last_activity || null,
                };
              }
            } catch (apiError) {
              console.log('Stats API not available, using mock data');
            }
            */

            return {
              _id: row.id, // For compatibility with existing code
              id: row.id,
              sub: row.id, // For compatibility
              email: row.email,
              name: row.name,
              username: row.username,
              role: row.role || 'user',
              emailVerified: row.emailVerified,
              createdAt: row.createdAt,
              updatedAt: row.updatedAt,
              ...stats,
            };
          } catch (error) {
            console.error(`Error fetching stats for user ${row.id}:`, error);
            // Return user without stats if API call fails
            return {
              _id: row.id,
              id: row.id,
              sub: row.id,
              email: row.email,
              name: row.name,
              username: row.username,
              role: row.role || 'user',
              emailVerified: row.emailVerified,
              createdAt: row.createdAt,
              updatedAt: row.updatedAt,
              documentCount: 0,
              documentsCompleted: 0,
              documentsPending: 0,
              documentsProcessing: 0,
              documentsFailed: 0,
              lastActivity: null,
            };
          }
        })
      );

      // Sort in memory if needed for fields that come from external API
      let sortedUsers = usersWithStats;
      if (
        params.sortBy === 'lastActivity' ||
        params.sortBy === 'documentCount'
      ) {
        sortedUsers = usersWithStats.sort((a, b) => {
          let aValue: any, bValue: any;

          if (params.sortBy === 'lastActivity') {
            aValue = a.lastActivity ? new Date(a.lastActivity).getTime() : 0;
            bValue = b.lastActivity ? new Date(b.lastActivity).getTime() : 0;
          } else if (params.sortBy === 'documentCount') {
            aValue = a.documentCount || 0;
            bValue = b.documentCount || 0;
          }

          if (params.sortOrder === 'asc') {
            return aValue - bValue;
          } else {
            return bValue - aValue;
          }
        });
      }

      const response = {
        users: sortedUsers,
        total,
        page: params.page,
        pageSize: params.pageSize,
        totalPages: Math.ceil(total / params.pageSize),
      };

      await pool.end();
      return NextResponse.json({
        success: true,
        data: response,
      });
    } catch (dbError) {
      await pool.end();
      throw dbError;
    }
  } catch (error) {
    console.error('Error fetching users:', error);
    return NextResponse.json(
      {
        success: false,
        error: 'Failed to fetch users',
      },
      { status: 500 }
    );
  }
}

// Apply RBAC middleware requiring admin role
export const GET = withRBAC(getUsersHandler, { requiredRole: 'admin' });
