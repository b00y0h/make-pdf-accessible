'use client';

import dynamic from 'next/dynamic';
import { Upload, FileText, CheckCircle, Zap, ArrowDown } from 'lucide-react';
import UserAvatar from '../components/UserAvatar';

// Dynamically import PDFProcessor to avoid SSR issues
const PDFProcessor = dynamic(() => import('../components/PDFProcessor'), {
  ssr: false,
});

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50">
      {/* Header with User Avatar */}
      <header className="absolute top-0 right-0 p-4 z-10">
        <UserAvatar />
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Hero section */}
        <div className="pt-16 pb-8 text-center">
          <h1 className="text-4xl tracking-tight font-extrabold text-gray-900 sm:text-5xl md:text-6xl">
            <span className="block">Make Your PDFs</span>
            <span className="block text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-indigo-600">
              Instantly Accessible
            </span>
          </h1>
          <p className="mt-3 max-w-md mx-auto text-base text-gray-600 sm:text-lg md:mt-5 md:text-xl md:max-w-3xl">
            AI-powered PDF accessibility in seconds. No signup required.
            Upload your PDF below and see the magic happen!
          </p>
          
          {/* Arrow pointing down */}
          <div className="mt-8 animate-bounce">
            <ArrowDown className="w-8 h-8 text-blue-600 mx-auto" />
          </div>
        </div>

        {/* Main Upload Section - The primary CTA */}
        <div className="pb-16">
          <PDFProcessor />
        </div>

        {/* Features */}
        <div className="py-16 bg-white rounded-lg shadow-lg">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center">
              <h2 className="text-3xl font-extrabold text-gray-900">
                How it works
              </h2>
              <p className="mt-4 text-lg text-gray-500">
                Simple, fast, and accessible document processing
              </p>
            </div>

            <div className="mt-16">
              <div className="grid grid-cols-1 gap-8 md:grid-cols-3">
                <div className="text-center">
                  <div className="flex items-center justify-center h-16 w-16 rounded-md bg-blue-500 text-white mx-auto">
                    <Upload className="h-8 w-8" />
                  </div>
                  <h3 className="mt-6 text-lg font-medium text-gray-900">
                    Upload Files
                  </h3>
                  <p className="mt-2 text-base text-gray-500">
                    Drag and drop your PDF, Word, or text files. Direct upload
                    to secure cloud storage with progress tracking.
                  </p>
                </div>

                <div className="text-center">
                  <div className="flex items-center justify-center h-16 w-16 rounded-md bg-blue-500 text-white mx-auto">
                    <Zap className="h-8 w-8" />
                  </div>
                  <h3 className="mt-6 text-lg font-medium text-gray-900">
                    AI Processing
                  </h3>
                  <p className="mt-2 text-base text-gray-500">
                    Automated accessibility processing using OCR, structure
                    analysis, and AI-powered improvements.
                  </p>
                </div>

                <div className="text-center">
                  <div className="flex items-center justify-center h-16 w-16 rounded-md bg-blue-500 text-white mx-auto">
                    <CheckCircle className="h-8 w-8" />
                  </div>
                  <h3 className="mt-6 text-lg font-medium text-gray-900">
                    Download Results
                  </h3>
                  <p className="mt-2 text-base text-gray-500">
                    Get accessible PDFs, HTML, and alternative formats. Track
                    progress with live updates.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* CTA */}
        <div className="py-16">
          <div className="max-w-2xl mx-auto text-center">
            <h2 className="text-3xl font-extrabold text-gray-900">
              Ready to make your PDFs accessible?
            </h2>
            <p className="mt-4 text-lg text-gray-500">
              Scroll up to try it now - no signup required!
            </p>
            <div className="mt-8">
              <button
                onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
                className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transform hover:-translate-y-0.5 transition-all duration-200"
              >
                <Upload className="w-5 h-5 mr-2" />
                Try It Now
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
