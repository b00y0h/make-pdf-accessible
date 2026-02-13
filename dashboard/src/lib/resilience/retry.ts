export interface RetryOptions {
  maxRetries?: number;
  baseDelay?: number; // Base delay in milliseconds
  maxDelay?: number; // Maximum delay in milliseconds
  backoffFactor?: number; // Exponential backoff multiplier
  jitter?: boolean; // Add random jitter to delays
  retryCondition?: (error: any) => boolean; // Function to determine if error should be retried
}

export interface RetryResult<T> {
  result: T;
  attempts: number;
  totalTime: number;
}

const DEFAULT_OPTIONS: Required<RetryOptions> = {
  maxRetries: 3,
  baseDelay: 1000, // 1 second
  maxDelay: 30000, // 30 seconds
  backoffFactor: 2,
  jitter: true,
  retryCondition: (error: any) => {
    // Retry on network errors, timeouts, and 5xx server errors
    if (
      error?.code === 'ECONNRESET' ||
      error?.code === 'ETIMEDOUT' ||
      error?.code === 'ENOTFOUND'
    ) {
      return true;
    }

    // Retry on HTTP 5xx errors and 429 (too many requests)
    if (error?.status >= 500 || error?.status === 429) {
      return true;
    }

    // Retry on specific AWS errors
    if (
      error?.name === 'ThrottlingException' ||
      error?.name === 'TooManyRequestsException' ||
      error?.name === 'ServiceUnavailableException'
    ) {
      return true;
    }

    return false;
  },
};

export class RetryableError extends Error {
  constructor(
    message: string,
    public originalError?: any
  ) {
    super(message);
    this.name = 'RetryableError';
  }
}

export class NonRetryableError extends Error {
  constructor(
    message: string,
    public originalError?: any
  ) {
    super(message);
    this.name = 'NonRetryableError';
  }
}

export async function withRetry<T>(
  operation: () => Promise<T>,
  options: RetryOptions = {}
): Promise<RetryResult<T>> {
  const opts = { ...DEFAULT_OPTIONS, ...options };
  const startTime = Date.now();
  let lastError: any;

  for (let attempt = 1; attempt <= opts.maxRetries + 1; attempt++) {
    try {
      const result = await operation();
      return {
        result,
        attempts: attempt,
        totalTime: Date.now() - startTime,
      };
    } catch (error) {
      lastError = error;

      // Don't retry on the last attempt or if error is not retryable
      if (attempt > opts.maxRetries || !opts.retryCondition(error)) {
        break;
      }

      // Calculate delay with exponential backoff
      const baseDelay =
        opts.baseDelay * Math.pow(opts.backoffFactor, attempt - 1);
      const delay = Math.min(baseDelay, opts.maxDelay);

      // Add jitter to prevent thundering herd
      const jitteredDelay = opts.jitter
        ? delay * (0.5 + Math.random() * 0.5)
        : delay;

      console.warn(
        `Operation failed on attempt ${attempt}, retrying in ${Math.round(jitteredDelay)}ms:`,
        {
          error: error instanceof Error ? error.message : String(error),
          attempt,
          maxRetries: opts.maxRetries,
        }
      );

      await sleep(jitteredDelay);
    }
  }

  // All retries exhausted
  const totalTime = Date.now() - startTime;
  console.error(
    `Operation failed after ${opts.maxRetries + 1} attempts in ${totalTime}ms:`,
    lastError
  );

  throw new RetryableError(
    `Operation failed after ${opts.maxRetries + 1} attempts: ${lastError?.message || 'Unknown error'}`,
    lastError
  );
}

export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// Specialized retry for AWS Cost Explorer API
export async function withCostExplorerRetry<T>(
  operation: () => Promise<T>,
  options: Partial<RetryOptions> = {}
): Promise<RetryResult<T>> {
  return withRetry(operation, {
    maxRetries: 3,
    baseDelay: 2000, // Start with 2 seconds
    maxDelay: 60000, // Max 1 minute
    backoffFactor: 2,
    jitter: true,
    retryCondition: (error: any) => {
      // Cost Explorer specific retry conditions
      if (error?.name === 'LimitExceededException') return true;
      if (error?.name === 'ThrottlingException') return true;
      if (error?.name === 'ServiceUnavailableException') return true;
      if (error?.message?.includes('Rate exceeded')) return true;

      // HTTP status codes
      if (error?.status === 429) return true; // Too many requests
      if (error?.status >= 500) return true; // Server errors

      return false;
    },
    ...options,
  });
}

// Specialized retry for Athena queries
export async function withAthenaRetry<T>(
  operation: () => Promise<T>,
  options: Partial<RetryOptions> = {}
): Promise<RetryResult<T>> {
  return withRetry(operation, {
    maxRetries: 5, // Athena queries can take longer
    baseDelay: 3000, // Start with 3 seconds
    maxDelay: 120000, // Max 2 minutes
    backoffFactor: 1.5, // More gradual backoff
    jitter: true,
    retryCondition: (error: any) => {
      // Athena specific retry conditions
      if (error?.name === 'TooManyRequestsException') return true;
      if (error?.name === 'InternalServerException') return true;
      if (error?.message?.includes('Query execution was interrupted'))
        return true;
      if (error?.message?.includes('Query timed out')) return true;

      // Don't retry on query syntax errors or permission issues
      if (error?.name === 'InvalidRequestException') return false;
      if (error?.name === 'AccessDeniedException') return false;
      if (error?.message?.includes('SYNTAX_ERROR')) return false;

      // HTTP status codes
      if (error?.status === 429) return true;
      if (error?.status >= 500) return true;

      return false;
    },
    ...options,
  });
}

// Circuit breaker implementation
export class CircuitBreaker {
  private failures = 0;
  private nextAttempt = Date.now();
  private state: 'CLOSED' | 'OPEN' | 'HALF_OPEN' = 'CLOSED';

  constructor(
    private failureThreshold = 5,
    private recoveryTimeout = 60000, // 1 minute
    private monitoringPeriod = 300000 // 5 minutes
  ) {}

  async execute<T>(operation: () => Promise<T>): Promise<T> {
    if (this.state === 'OPEN') {
      if (Date.now() < this.nextAttempt) {
        throw new NonRetryableError('Circuit breaker is OPEN');
      }
      this.state = 'HALF_OPEN';
    }

    try {
      const result = await operation();
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure();
      throw error;
    }
  }

  private onSuccess(): void {
    this.failures = 0;
    this.state = 'CLOSED';
  }

  private onFailure(): void {
    this.failures += 1;

    if (this.failures >= this.failureThreshold) {
      this.state = 'OPEN';
      this.nextAttempt = Date.now() + this.recoveryTimeout;
    }
  }

  getState(): { state: string; failures: number; nextAttempt: number } {
    return {
      state: this.state,
      failures: this.failures,
      nextAttempt: this.nextAttempt,
    };
  }

  reset(): void {
    this.failures = 0;
    this.state = 'CLOSED';
    this.nextAttempt = Date.now();
  }
}

// Global circuit breakers for different services
export const costExplorerCircuitBreaker = new CircuitBreaker(5, 60000, 300000);
export const athenaCircuitBreaker = new CircuitBreaker(3, 120000, 300000);
