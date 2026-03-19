import React from 'react';
import { Card } from '../molecules/Card';

export interface ImageEvidenceGalleryProps {
  images: string[];
  title?: string;
}

export const ImageEvidenceGallery: React.FC<ImageEvidenceGalleryProps> = ({
  images,
  title = 'Image evidence',
}) => {
  return (
    <Card className="p-4">
      <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">{title}</h3>
      {images.length === 0 ? (
        <p className="text-sm text-gray-500 dark:text-gray-400">No image evidence available.</p>
      ) : (
        <ul className="grid grid-cols-2 md:grid-cols-3 gap-3" role="list">
          {images.map((image, index) => (
            <li key={`${image}-${index}`}>
              <a
                href={image}
                target="_blank"
                rel="noreferrer"
                className="block rounded-md border border-gray-200 dark:border-gray-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={image}
                  alt={`Evidence ${index + 1}`}
                  className="h-28 w-full rounded-md object-cover"
                  loading="lazy"
                />
              </a>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
};

ImageEvidenceGallery.displayName = 'ImageEvidenceGallery';
