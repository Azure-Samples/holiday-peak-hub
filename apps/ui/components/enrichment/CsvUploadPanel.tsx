'use client';

import React, { useCallback, useRef, useState } from 'react';
import { Card } from '@/components/molecules/Card';

type UploadState = 'idle' | 'uploading' | 'success' | 'error';

const API_URL = process.env.NEXT_PUBLIC_API_URL || '';

export const CsvUploadPanel: React.FC = () => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadState, setUploadState] = useState<UploadState>('idle');
  const [errorMessage, setErrorMessage] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] ?? null;
    setSelectedFile(file);
    setUploadState('idle');
    setErrorMessage('');
  }, []);

  const handleUpload = useCallback(async () => {
    if (!selectedFile) return;

    setUploadState('uploading');
    setErrorMessage('');

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);

      const response = await fetch(`${API_URL}/api/demo/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const body = await response.text().catch(() => '');
        throw new Error(body || `Upload failed (${response.status})`);
      }

      setUploadState('success');
    } catch (err) {
      setUploadState('error');
      setErrorMessage(err instanceof Error ? err.message : 'Upload failed');
    }
  }, [selectedFile]);

  const fileSizeKb = selectedFile ? (selectedFile.size / 1024).toFixed(1) : null;

  return (
    <Card className="overflow-hidden">
      <button
        type="button"
        onClick={() => setIsExpanded((prev) => !prev)}
        aria-expanded={isExpanded}
        aria-controls="csv-upload-panel-content"
        className="flex w-full items-center justify-between px-4 py-3 text-left text-sm font-semibold text-gray-900 dark:text-white hover:bg-gray-50 dark:hover:bg-gray-800/40 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
      >
        <span>Demo: Upload Products</span>
        <svg
          className={`h-4 w-4 text-gray-500 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          aria-hidden="true"
        >
          <path
            fillRule="evenodd"
            d="M5.22 8.22a.75.75 0 0 1 1.06 0L10 11.94l3.72-3.72a.75.75 0 1 1 1.06 1.06l-4.25 4.25a.75.75 0 0 1-1.06 0L5.22 9.28a.75.75 0 0 1 0-1.06Z"
            clipRule="evenodd"
          />
        </svg>
      </button>

      {isExpanded && (
        <div id="csv-upload-panel-content" className="border-t border-gray-200 dark:border-gray-700 px-4 py-4 space-y-4">
          <div>
            <label htmlFor="csv-file-input" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Select CSV file
            </label>
            <input
              id="csv-file-input"
              ref={fileInputRef}
              type="file"
              accept=".csv"
              onChange={handleFileChange}
              className="block w-full text-sm text-gray-600 dark:text-gray-400 file:mr-3 file:rounded-md file:border file:border-gray-300 dark:file:border-gray-600 file:bg-gray-50 dark:file:bg-gray-800 file:px-3 file:py-1.5 file:text-sm file:font-semibold file:text-gray-700 dark:file:text-gray-300 hover:file:bg-gray-100 dark:hover:file:bg-gray-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
            />
          </div>

          {selectedFile && (
            <p className="text-xs text-gray-500 dark:text-gray-400">
              <span className="font-medium text-gray-700 dark:text-gray-300">{selectedFile.name}</span>
              {' — '}
              {fileSizeKb} KB
            </p>
          )}

          <button
            type="button"
            onClick={() => void handleUpload()}
            disabled={!selectedFile || uploadState === 'uploading'}
            className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {uploadState === 'uploading' && (
              <svg className="h-4 w-4 animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" aria-hidden="true">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            )}
            Upload &amp; Trigger Pipeline
          </button>

          {uploadState === 'success' && (
            <p className="text-sm font-medium text-green-600 dark:text-green-400" role="status">
              Upload successful — pipeline triggered.
            </p>
          )}

          {uploadState === 'error' && (
            <p className="text-sm font-medium text-red-600 dark:text-red-400" role="alert">
              {errorMessage || 'Upload failed. Please try again.'}
            </p>
          )}
        </div>
      )}
    </Card>
  );
};
