import { MongoClient, Db, ObjectId } from 'mongodb';
import {
  User,
  UserSummary,
  UserListParams,
  UserListResponse,
  Document,
  AuditLog,
  DeletionJob,
} from '../types/admin';

const uri =
  process.env.MONGODB_URI ||
  'mongodb://localhost:27017/pdf_accessibility?replicaSet=rs0';
const dbName = process.env.MONGODB_DATABASE || 'pdf_accessibility';

const client = new MongoClient(uri);
let db: Db;

// Global connection for NextJS
declare global {
  var _mongoClient: MongoClient | undefined;
}

if (process.env.NODE_ENV === 'development') {
  if (!global._mongoClient) {
    global._mongoClient = client;
  }
}

export async function connectToDatabase() {
  if (!db) {
    await client.connect();
    db = client.db(dbName);
  }
  return { client, db };
}

// Admin repository functions
export class AdminRepository {
  private db: Db;

  constructor(database: Db) {
    this.db = database;
  }

  async getUsers(params: UserListParams): Promise<UserListResponse> {
    const {
      page = 1,
      pageSize = 20,
      search,
      sortBy = 'createdAt',
      sortOrder = 'desc',
      role,
    } = params;

    const skip = (page - 1) * pageSize;
    const usersCollection = this.db.collection<User>('users');

    // Build filter
    const filter: any = {};
    if (search) {
      filter.$or = [
        { email: { $regex: search, $options: 'i' } },
        { name: { $regex: search, $options: 'i' } },
        { username: { $regex: search, $options: 'i' } },
      ];
    }
    if (role) {
      filter.role = role;
    }

    // Build sort
    const sort: any = {};
    sort[sortBy] = sortOrder === 'desc' ? -1 : 1;

    // Get users with document counts
    const pipeline: any[] = [
      { $match: filter },
      {
        $lookup: {
          from: 'documents',
          localField: 'sub',
          foreignField: 'ownerId',
          as: 'documents',
        },
      },
      {
        $addFields: {
          documentCount: { $size: '$documents' },
          documentsCompleted: {
            $size: {
              $filter: {
                input: '$documents',
                as: 'doc',
                cond: { $eq: ['$$doc.status', 'completed'] },
              },
            },
          },
          documentsPending: {
            $size: {
              $filter: {
                input: '$documents',
                as: 'doc',
                cond: { $eq: ['$$doc.status', 'pending'] },
              },
            },
          },
          documentsProcessing: {
            $size: {
              $filter: {
                input: '$documents',
                as: 'doc',
                cond: { $eq: ['$$doc.status', 'processing'] },
              },
            },
          },
          documentsFailed: {
            $size: {
              $filter: {
                input: '$documents',
                as: 'doc',
                cond: {
                  $in: [
                    '$$doc.status',
                    ['failed', 'validation_failed', 'notification_failed'],
                  ],
                },
              },
            },
          },
          lastActivity: { $max: '$documents.updatedAt' },
        },
      },
      { $unset: 'documents' },
      { $sort: sort },
      {
        $facet: {
          data: [{ $skip: skip }, { $limit: pageSize }],
          count: [{ $count: 'total' }],
        },
      },
    ];

    const result = await usersCollection.aggregate(pipeline).toArray();
    const users = result[0]?.data || [];
    const total = result[0]?.count[0]?.total || 0;
    const totalPages = Math.ceil(total / pageSize);

    return {
      users: users as UserSummary[],
      total,
      page,
      pageSize,
      totalPages,
    };
  }

  async getUserById(userId: string): Promise<UserSummary | null> {
    const usersCollection = this.db.collection<User>('users');
    const pipeline = [
      { $match: { _id: new ObjectId(userId) } },
      {
        $lookup: {
          from: 'documents',
          localField: 'sub',
          foreignField: 'ownerId',
          as: 'documents',
        },
      },
      {
        $addFields: {
          documentCount: { $size: '$documents' },
          documentsCompleted: {
            $size: {
              $filter: {
                input: '$documents',
                as: 'doc',
                cond: { $eq: ['$$doc.status', 'completed'] },
              },
            },
          },
          documentsPending: {
            $size: {
              $filter: {
                input: '$documents',
                as: 'doc',
                cond: { $eq: ['$$doc.status', 'pending'] },
              },
            },
          },
          documentsProcessing: {
            $size: {
              $filter: {
                input: '$documents',
                as: 'doc',
                cond: { $eq: ['$$doc.status', 'processing'] },
              },
            },
          },
          documentsFailed: {
            $size: {
              $filter: {
                input: '$documents',
                as: 'doc',
                cond: {
                  $in: [
                    '$$doc.status',
                    ['failed', 'validation_failed', 'notification_failed'],
                  ],
                },
              },
            },
          },
          lastActivity: { $max: '$documents.updatedAt' },
        },
      },
      { $unset: 'documents' },
    ];

    const result = await usersCollection.aggregate(pipeline).toArray();
    return (result[0] as UserSummary) || null;
  }

  async deleteUser(userId: string, actorUserId: string): Promise<DeletionJob> {
    const session = client.startSession();

    try {
      return await session.withTransaction(async () => {
        const usersCollection = this.db.collection<User>('users');
        const documentsCollection = this.db.collection<Document>('documents');
        const deletionJobsCollection =
          this.db.collection<DeletionJob>('deletionJobs');
        const auditLogsCollection = this.db.collection<AuditLog>('auditLogs');

        // Get user to delete
        const user = await usersCollection.findOne({
          _id: new ObjectId(userId),
        });
        if (!user) {
          throw new Error('User not found');
        }

        // Create deletion job
        const deletionJob: Omit<DeletionJob, '_id'> = {
          targetUserId: userId,
          status: 'pending',
          createdAt: new Date(),
          updatedAt: new Date(),
        };

        const jobResult = await deletionJobsCollection.insertOne(deletionJob);
        const jobId = jobResult.insertedId.toString();

        // Create audit log
        await auditLogsCollection.insertOne({
          actorUserId,
          action: 'admin.delete_user_started',
          targetUserId: userId,
          meta: {
            userEmail: user.email,
            deletionJobId: jobId,
          },
          createdAt: new Date(),
        });

        // Start deletion process
        try {
          await deletionJobsCollection.updateOne(
            { _id: jobResult.insertedId },
            {
              $set: {
                status: 'running',
                startedAt: new Date(),
                updatedAt: new Date(),
              },
            }
          );

          // Find and count documents to delete
          const userDocuments = await documentsCollection
            .find({ ownerId: user.sub || userId })
            .toArray();
          const documentCount = userDocuments.length;

          // Delete documents
          if (documentCount > 0) {
            await documentsCollection.deleteMany({
              ownerId: user.sub || userId,
            });
          }

          // Delete user
          await usersCollection.deleteOne({ _id: new ObjectId(userId) });

          // Update job as completed
          const finishedAt = new Date();
          await deletionJobsCollection.updateOne(
            { _id: jobResult.insertedId },
            {
              $set: {
                status: 'done',
                finishedAt,
                updatedAt: finishedAt,
                meta: {
                  deletedDocuments: documentCount,
                },
              },
            }
          );

          // Create completion audit log
          await auditLogsCollection.insertOne({
            actorUserId,
            action: 'admin.delete_user_completed',
            targetUserId: userId,
            meta: {
              userEmail: user.email,
              deletionJobId: jobId,
              deletedDocuments: documentCount,
            },
            createdAt: new Date(),
          });

          return {
            _id: jobResult.insertedId,
            ...deletionJob,
            status: 'done',
            startedAt: new Date(),
            finishedAt,
            meta: {
              deletedDocuments: documentCount,
            },
          } as DeletionJob;
        } catch (error) {
          // Mark job as failed
          await deletionJobsCollection.updateOne(
            { _id: jobResult.insertedId },
            {
              $set: {
                status: 'failed',
                finishedAt: new Date(),
                updatedAt: new Date(),
                error: error instanceof Error ? error.message : 'Unknown error',
              },
            }
          );

          throw error;
        }
      });
    } finally {
      await session.endSession();
    }
  }

  async createAuditLog(
    auditLog: Omit<AuditLog, '_id' | 'createdAt'>
  ): Promise<void> {
    const auditLogsCollection = this.db.collection<AuditLog>('auditLogs');
    await auditLogsCollection.insertOne({
      ...auditLog,
      createdAt: new Date(),
    });
  }
}

export async function getAdminRepository(): Promise<AdminRepository> {
  const { db } = await connectToDatabase();
  return new AdminRepository(db);
}

export { client, db };
