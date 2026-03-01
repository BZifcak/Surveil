import React, { useMemo, useState } from 'react';
import './Cam.css';

interface CameraGridProps {
  columns?: number;
  cameraCount?: number;
  images?: string[];
  selected?: number;
  onSelect?: (id: number) => void;
}

function CameraTile({
  id,
  src,
  large = false,
  selected = false,
  onClick,
}: {
  id: number;
  src?: string;
  large?: boolean;
  selected?: boolean;
  onClick?: () => void;
}) {
  return (
    <button
      type="button"
      className={`cam-tile ${large ? 'cam-tile--large' : ''} ${selected ? 'cam-tile--selected' : ''}`}
      onClick={onClick}
    >
      {src ? (
        <img src={src} alt={`Camera ${id}`} className="cam-image" />
      ) : (
        <div className="cam-empty">
          <span className="cam-empty-icon">CAM</span>
          <span>No Signal</span>
        </div>
      )}
      <div className="cam-label">CAM {id}</div>
    </button>
  );
}

const CameraGrid: React.FC<CameraGridProps> = ({
  columns = 4,
  cameraCount = 4,
  images = [],
  selected,
  onSelect,
}) => {
  const cameras = useMemo(
    () =>
      Array.from({ length: cameraCount }, (_, i) => ({
        id: i + 1,
        src: images.length ? images[i % images.length] : undefined,
      })),
    [cameraCount, images]
  );

  const [internalSelected, setInternalSelected] = useState<number>(1);
  const selectedId = selected ?? internalSelected;
  const activeId = cameras.some((cam) => cam.id === selectedId) ? selectedId : cameras[0]?.id;
  const featured = cameras.find((cam) => cam.id === activeId) ?? cameras[0];

  const handleSelect = (id: number) => {
    setInternalSelected(id);
    onSelect?.(id);
  };

  if (!featured) {
    return null;
  }

  return (
    <div className="cam-layout">
      <div className="cam-featured">
        <CameraTile
          id={featured.id}
          src={featured.src}
          large
          selected
          onClick={() => handleSelect(featured.id)}
        />
      </div>

      <div className="cam-selector-dock">
        <button type="button" className="cam-selector-handle" aria-label="Open camera selector">
          Cameras
        </button>
        <div className="cam-selector-tray">
          <div className="cam-grid cam-grid--tray" style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }}>
            {cameras.map((cam) => (
              <CameraTile
                key={cam.id}
                id={cam.id}
                src={cam.src}
                selected={cam.id === activeId}
                onClick={() => handleSelect(cam.id)}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default CameraGrid;
