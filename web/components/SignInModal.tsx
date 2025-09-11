'use client';

import React, { useEffect } from 'react';
import { X, Shield } from 'lucide-react';

interface SignInModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export default function SignInModal({ isOpen, onClose, onSuccess }: SignInModalProps) {
  useEffect(() => {
    if (isOpen) {
      // Listen for messages from the popup window
      const handleMessage = (event: MessageEvent) => {
        // Verify the message is from the dashboard
        if (event.origin === 'http://localhost:3001') {
          if (event.data.type === 'auth-success') {
            // Authentication successful
            onSuccess();
            onClose();
          }
        }
      };

      window.addEventListener('message', handleMessage);
      return () => window.removeEventListener('message', handleMessage);
    }
  }, [isOpen, onSuccess, onClose]);

  if (!isOpen) return null;

  const openAuthPopup = () => {
    // Open dashboard sign-in in a popup window
    const width = 500;
    const height = 700;
    const left = window.screen.width / 2 - width / 2;
    const top = window.screen.height / 2 - height / 2;
    
    const popup = window.open(
      'http://localhost:3001/sign-in?popup=true&callback=marketing',
      'Sign In',
      `width=${width},height=${height},left=${left},top=${top},toolbar=no,menubar=no`
    );

    // Check if popup was blocked
    if (!popup) {
      // Fallback to redirect if popup is blocked
      window.location.href = 'http://localhost:3001/sign-in?callback=' + encodeURIComponent(window.location.href);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-8 relative text-center">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-400 hover:text-gray-600"
        >
          <X className="w-6 h-6" />
        </button>

        <div className="flex justify-center mb-6">
          <div className="h-16 w-16 rounded-xl bg-gradient-to-br from-blue-600 to-cyan-600 flex items-center justify-center">
            <Shield className="h-10 w-10 text-white" />
          </div>
        </div>

        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          Sign In to Continue
        </h2>
        
        <p className="text-gray-600 mb-8">
          Sign in to download your accessible PDF and save your documents for future access.
        </p>

        <button
          onClick={openAuthPopup}
          className="w-full py-3 px-4 bg-gradient-to-r from-blue-600 to-cyan-600 text-white rounded-lg hover:from-blue-700 hover:to-cyan-700 transition-colors font-medium"
        >
          Open Sign In
        </button>

        <p className="mt-6 text-sm text-gray-500">
          You'll be redirected to our secure sign-in page with multiple authentication options including Google, GitHub, and more.
        </p>
      </div>
    </div>
  );
}