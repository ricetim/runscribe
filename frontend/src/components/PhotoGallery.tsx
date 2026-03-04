import { useState } from "react";
import { Photo } from "../types";

interface Props {
  photos: Photo[];
}

export default function PhotoGallery({ photos }: Props) {
  const [lightbox, setLightbox] = useState<string | null>(null);

  if (!photos.length) return null;

  return (
    <div>
      <h2 className="text-lg font-semibold text-gray-800 mb-3">Photos</h2>
      <div className="flex gap-2 flex-wrap">
        {photos.map((p) => (
          <div key={p.id} className="relative group">
            <img
              src={p.url}
              alt="Run photo"
              className="h-28 w-28 object-cover rounded-lg cursor-pointer border border-gray-200 hover:opacity-90 transition-opacity"
              onClick={() => setLightbox(p.url)}
            />
            {/* GPS indicator badge */}
            {p.lat !== null && (
              <span
                className="absolute bottom-1 right-1 text-xs bg-black/60 text-white px-1 rounded"
                title="Has GPS location"
              >
                📍
              </span>
            )}
          </div>
        ))}
      </div>

      {/* Lightbox */}
      {lightbox && (
        <div
          className="fixed inset-0 bg-black/85 flex items-center justify-center z-50 p-4"
          onClick={() => setLightbox(null)}
        >
          <img
            src={lightbox}
            alt="Run photo"
            className="max-h-screen max-w-full rounded-lg shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          />
          <button
            className="absolute top-4 right-4 text-white text-2xl font-bold w-10 h-10 flex items-center justify-center bg-black/40 rounded-full hover:bg-black/60"
            onClick={() => setLightbox(null)}
          >
            ×
          </button>
        </div>
      )}
    </div>
  );
}
