import React from 'react';

interface CameraGridProps {
  columns?: number;
  cameraCount?: number;
  images?: string[];
}

const CameraGrid: React.FC<CameraGridProps> = ({ 
  columns = 2, 
  cameraCount = 4,
  images = []
}) => {
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: `repeat(${columns}, 1fr)`,
      gap: '12px',
      background: '#1a1a1a',
      padding: '12px'
    }}>
      {Array.from({ length: cameraCount }).map((_, i) => {
        const src = images[i % images.length] // ✅ cycles through images
        return (
          <div key={i} style={{ 
            background: '#000', 
            borderRadius: '4px', 
            overflow: 'hidden',
            position: 'relative'
          }}>
            {src ? (
              <img
                src={src}
                alt={`Camera ${i + 1}`}
                style={{ width: '100%', display: 'block', objectFit: 'cover', aspectRatio: '16/9' }}
              />
            ) : (
              <div style={{
                width: '100%',
                aspectRatio: '16/9',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#444',
                fontSize: '14px',
                flexDirection: 'column',
                gap: '8px'
              }}>
                <span style={{ fontSize: '32px' }}>📷</span>
                <span>No Signal</span>
              </div>
            )}
            <div style={{
              position: 'absolute',
              bottom: '8px',
              left: '8px',
              background: 'rgba(0,0,0,0.6)',
              color: '#fff',
              fontSize: '12px',
              padding: '2px 8px',
              borderRadius: '4px'
            }}>
              CAM {i + 1}
            </div>
          </div>
        )
      })}
    </div>
  );
};

export default CameraGrid;