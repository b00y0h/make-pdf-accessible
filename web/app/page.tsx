import Link from 'next/link';
import { Upload, FileText, CheckCircle, Zap } from 'lucide-react';

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Hero section */}
        <div className="pt-20 pb-16 text-center">
          <h1 className="text-4xl tracking-tight font-extrabold text-gray-900 sm:text-5xl md:text-6xl">
            <span className="block">Make PDFs</span>
            <span className="block text-blue-600">Accessible</span>
          </h1>
          <p className="mt-3 max-w-md mx-auto text-base text-gray-500 sm:text-lg md:mt-5 md:text-xl md:max-w-3xl">
            Transform your PDFs into accessible formats with automated
            processing. Upload, process, and download accessible documents in
            seconds.
          </p>
          <div className="mt-8 max-w-md mx-auto sm:flex sm:justify-center md:mt-12">
            <div className="rounded-md shadow">
              <Link
                href="/upload"
                className="w-full flex items-center justify-center px-8 py-3 border border-transparent text-base font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 md:py-4 md:text-lg md:px-10 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
              >
                <Upload className="w-5 h-5 mr-2" />
                Upload Documents
              </Link>
            </div>
          </div>
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
              Ready to get started?
            </h2>
            <p className="mt-4 text-lg text-gray-500">
              Upload your first document and see the magic happen.
            </p>
            <div className="mt-8">
              <Link
                href="/upload"
                className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
              >
                <FileText className="w-5 h-5 mr-2" />
                Start Processing
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
