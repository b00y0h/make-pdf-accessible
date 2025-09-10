import { NextRequest } from 'next/server'
import { withRBAC } from '@/lib/rbac-middleware'
import { UserListParams } from '@/types/admin'
import { Pool } from 'pg'

async function getUsersHandler(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    
    // Parse query parameters
    const params: UserListParams = {
      page: parseInt(searchParams.get('page') || '1'),
      pageSize: Math.min(parseInt(searchParams.get('pageSize') || '20'), 100), // Max 100 per page
      search: searchParams.get('search') || undefined,
      sortBy: (searchParams.get('sortBy') as any) || 'createdAt',
      sortOrder: (searchParams.get('sortOrder') as 'asc' | 'desc') || 'desc',
      role: (searchParams.get('role') as 'admin' | 'user') || undefined,
    }

    // Connect to BetterAuth PostgreSQL database
    const pool = new Pool({
      connectionString: process.env.AUTH_DATABASE_URL || "postgresql://postgres:password@localhost:5433/better_auth",
    })

    try {
      // Build query
      let query = 'SELECT id, email, name, username, role, "emailVerified", "createdAt", "updatedAt" FROM "user"'
      let conditions: string[] = []
      let values: any[] = []
      let paramCount = 0

      // Add search condition
      if (params.search) {
        paramCount++
        conditions.push(`(email ILIKE $${paramCount} OR name ILIKE $${paramCount} OR username ILIKE $${paramCount})`)
        values.push(`%${params.search}%`)
      }

      // Add role filter
      if (params.role) {
        paramCount++
        conditions.push(`role = $${paramCount}`)
        values.push(params.role)
      }

      // Add WHERE clause if conditions exist
      if (conditions.length > 0) {
        query += ' WHERE ' + conditions.join(' AND ')
      }

      // Add ordering
      const sortColumn = params.sortBy === 'createdAt' ? '"createdAt"' : params.sortBy
      query += ` ORDER BY ${sortColumn} ${params.sortOrder.toUpperCase()}`

      // Add pagination
      const offset = (params.page - 1) * params.pageSize
      paramCount++
      query += ` LIMIT $${paramCount}`
      values.push(params.pageSize)

      paramCount++
      query += ` OFFSET $${paramCount}`
      values.push(offset)

      // Execute query
      const result = await pool.query(query, values)
      
      // Get total count
      let countQuery = 'SELECT COUNT(*) FROM "user"'
      let countValues: any[] = []
      let countParamCount = 0

      if (params.search) {
        countParamCount++
        countQuery += ` WHERE (email ILIKE $${countParamCount} OR name ILIKE $${countParamCount} OR username ILIKE $${countParamCount})`
        countValues.push(`%${params.search}%`)
        
        if (params.role) {
          countParamCount++
          countQuery += ` AND role = $${countParamCount}`
          countValues.push(params.role)
        }
      } else if (params.role) {
        countParamCount++
        countQuery += ` WHERE role = $${countParamCount}`
        countValues.push(params.role)
      }

      const countResult = await pool.query(countQuery, countValues)
      const total = parseInt(countResult.rows[0].count)

      const response = {
        users: result.rows.map(row => ({
          id: row.id,
          email: row.email,
          name: row.name,
          username: row.username,
          role: row.role || 'user',
          emailVerified: row.emailVerified,
          createdAt: row.createdAt,
          updatedAt: row.updatedAt
        })),
        total,
        page: params.page,
        pageSize: params.pageSize,
        totalPages: Math.ceil(total / params.pageSize)
      }

      await pool.end()
      return Response.json({
        success: true,
        data: response,
      })

    } catch (dbError) {
      await pool.end()
      throw dbError
    }

  } catch (error) {
    console.error('Error fetching users:', error)
    return Response.json(
      { 
        success: false,
        error: 'Failed to fetch users' 
      },
      { status: 500 }
    )
  }
}

// Apply RBAC middleware requiring admin role
export const GET = withRBAC(getUsersHandler, { requiredRole: 'admin' })