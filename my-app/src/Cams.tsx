import React, {useEffect, useRef} from "react"

export function CameraFeed(){
    const video = useRef<HTMLVideoElement>(null)
    useEffect(() => {
        navigator.mediaDevices.getUserMedia({ video: true })
          .then(stream => {
            if (video.current) video.current.srcObject = stream;
          })
          .catch(console.error);
      }, []);
    
      return <video ref={video} autoPlay playsInline style={{ width: '100%' }} />;
}