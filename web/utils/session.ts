/**
 * Session management utilities for demo uploads
 * 
 * Generates and manages browser session IDs for tracking anonymous uploads
 */

import { v4 as uuidv4 } from 'uuid';

const SESSION_ID_KEY = 'pdf_demo_session_id';
const SESSION_CREATED_KEY = 'pdf_demo_session_created';
const SESSION_UPLOADS_KEY = 'pdf_demo_uploads';

/**
 * Get or create a session ID for this browser
 */
export function getSessionId(): string {
  if (typeof window === 'undefined') {
    return 'server-side-render';
  }

  let sessionId = localStorage.getItem(SESSION_ID_KEY);
  
  if (!sessionId) {
    // Generate a new session ID
    sessionId = `session_${uuidv4()}`;
    localStorage.setItem(SESSION_ID_KEY, sessionId);
    localStorage.setItem(SESSION_CREATED_KEY, new Date().toISOString());
    localStorage.setItem(SESSION_UPLOADS_KEY, JSON.stringify([]));
  }
  
  return sessionId;
}

/**
 * Clear the current session (e.g., after user signs up)
 */
export function clearSession(): void {
  if (typeof window === 'undefined') return;
  
  localStorage.removeItem(SESSION_ID_KEY);
  localStorage.removeItem(SESSION_CREATED_KEY);
  localStorage.removeItem(SESSION_UPLOADS_KEY);
}

/**
 * Add an upload to the session history
 */
export function addUploadToSession(documentId: string, filename: string): void {
  if (typeof window === 'undefined') return;
  
  const uploadsStr = localStorage.getItem(SESSION_UPLOADS_KEY) || '[]';
  const uploads = JSON.parse(uploadsStr);
  
  uploads.push({
    documentId,
    filename,
    uploadedAt: new Date().toISOString(),
  });
  
  localStorage.setItem(SESSION_UPLOADS_KEY, JSON.stringify(uploads));
}

/**
 * Get all uploads from the current session
 */
export function getSessionUploads(): Array<{
  documentId: string;
  filename: string;
  uploadedAt: string;
}> {
  if (typeof window === 'undefined') return [];
  
  const uploadsStr = localStorage.getItem(SESSION_UPLOADS_KEY) || '[]';
  return JSON.parse(uploadsStr);
}

/**
 * Check if session has uploads
 */
export function hasSessionUploads(): boolean {
  return getSessionUploads().length > 0;
}

/**
 * Generate browser fingerprint components for additional tracking
 * This is a simple implementation - can be enhanced with libraries like FingerprintJS
 */
export function getBrowserFingerprint(): Record<string, any> {
  if (typeof window === 'undefined') {
    return {};
  }

  return {
    screen: {
      width: window.screen.width,
      height: window.screen.height,
      colorDepth: window.screen.colorDepth,
    },
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    language: navigator.language,
    platform: navigator.platform,
    userAgent: navigator.userAgent,
    cookieEnabled: navigator.cookieEnabled,
    doNotTrack: navigator.doNotTrack,
  };
}

/**
 * Headers to include with demo API requests
 */
export function getDemoHeaders(): Record<string, string> {
  return {
    'X-Session-ID': getSessionId(),
  };
}