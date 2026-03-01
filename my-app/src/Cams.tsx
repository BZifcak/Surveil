import React, { useMemo, useState } from 'react';
import './Cam.css';

interface CameraGridProps {
  columns?: number;
  cameraCount?: number;
  images?: string[];
  selected?: number;
  onSelect?: (id: number) => void;
  selectorOpen?: boolean;
  onSelectorOpenChange?: (open: boolean) => void;
  edgeToEdge?: boolean;
  panelPageIndex?: number;
  onPanelPageChange?: (page: number) => void;
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
          <span className="cam-empty-icon">CAM {id}</span>
          <span>No Signal</span>
        </div>
      )}
      <div className="cam-label">CAM {id}</div>
    </button>
  );
}

const CameraGrid: React.FC<CameraGridProps> = ({
  cameraCount = 4,
  images = [],
  selected,
  onSelect,
  selectorOpen,
  onSelectorOpenChange,
  edgeToEdge = false,
  panelPageIndex,
  onPanelPageChange,
}) => {
  const splitPageSize = 12;
  const panelPageSize = 4;
  const cameras = useMemo(
    () =>
      Array.from({ length: cameraCount }, (_, i) => ({
        id: i + 1,
        src: images[i],
      })),
    [cameraCount, images]
  );

  const [internalSelected, setInternalSelected] = useState<number>(1);
  const [internalSelectorOpen, setInternalSelectorOpen] = useState<boolean>(false);
  const [splitPageIndex, setSplitPageIndex] = useState<number>(0);
  const [internalPanelPageIndex, setInternalPanelPageIndex] = useState<number>(0);
  const isSelectorOpen = selectorOpen ?? internalSelectorOpen;
  const selectedId = selected ?? internalSelected;
  const activeId = cameras.some((cam) => cam.id === selectedId) ? selectedId : cameras[0]?.id;
  const featured = cameras.find((cam) => cam.id === activeId) ?? cameras[0];
  const splitPageCount = Math.max(1, Math.ceil(cameras.length / splitPageSize));
  const splitVisiblePage = Math.min(splitPageIndex, splitPageCount - 1);
  const splitPageStart = splitVisiblePage * splitPageSize;
  const splitPageCameras = cameras.slice(splitPageStart, splitPageStart + splitPageSize);
  const panelPageCount = Math.max(1, Math.ceil(cameras.length / panelPageSize));
  const panelVisiblePage = Math.min(panelPageIndex ?? internalPanelPageIndex, panelPageCount - 1);
  const panelPageStart = panelVisiblePage * panelPageSize;
  const panelPageCameras = cameras.slice(panelPageStart, panelPageStart + panelPageSize);

  const handleSelect = (id: number) => {
    setInternalSelected(id);
    onSelect?.(id);
  };

  const setSelectorOpen = (open: boolean) => {
    if (open) {
      const selectedPage = Math.floor((activeId - 1) / panelPageSize);
      setInternalPanelPageIndex(selectedPage);
      onPanelPageChange?.(selectedPage);
    }
    setInternalSelectorOpen(open);
    onSelectorOpenChange?.(open);
  };

  if (!featured) {
    return null;
  }

  if (edgeToEdge) {
    return (
      <div className="cam-layout cam-layout--edge">
        <div
          className="cam-grid cam-grid--split"
          style={{ gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gridTemplateRows: 'repeat(4, minmax(0, 1fr))' }}
        >
          {splitPageCameras.map((cam) => (
            <CameraTile
              key={cam.id}
              id={cam.id}
              src={cam.src}
              selected={cam.id === activeId}
              onClick={() => handleSelect(cam.id)}
            />
          ))}
        </div>

        <div className={`cam-page-panel ${isSelectorOpen ? 'cam-page-panel--open' : ''}`}>
          <div className="cam-page-list">
            {Array.from({ length: splitPageCount }, (_, i) => (
              <button
                key={i + 1}
                type="button"
                className={`cam-page-btn ${i === splitVisiblePage ? 'cam-page-btn--active' : ''}`}
                onClick={() => setSplitPageIndex(i)}
              >
                {i + 1}
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`cam-layout ${edgeToEdge ? 'cam-layout--edge' : ''}`}>
      <div className="cam-featured">
        <CameraTile
          id={featured.id}
          src={featured.src}
          large
          selected
          onClick={() => handleSelect(featured.id)}
        />
      </div>

      <div className={`cam-selector-panel ${isSelectorOpen ? 'cam-selector-panel--open' : ''}`}>
        <div className="cam-grid cam-grid--panel" style={{ gridTemplateColumns: 'repeat(2, minmax(0, 1fr))' }}>
          {panelPageCameras.map((cam) => (
            <CameraTile
              key={cam.id}
              id={cam.id}
              src={cam.src}
              selected={cam.id === activeId}
              onClick={() => {
                handleSelect(cam.id);
                setSelectorOpen(false);
              }}
            />
          ))}
        </div>
      </div>
    </div>
  );
};

export default CameraGrid;
