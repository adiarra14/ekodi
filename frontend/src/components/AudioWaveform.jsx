import { useRef, useEffect } from 'react';
import './AudioWaveform.css';

/**
 * Real-time audio waveform visualizer using canvas.
 *
 * Props:
 *  - analyserNode : Web Audio AnalyserNode (required when active)
 *  - active       : boolean – animate when true
 *  - color        : bar colour (default '#ff7a2f')
 *  - barWidth     : width of each bar in px (default 3)
 *  - barGap       : gap between bars in px (default 2)
 *  - height       : canvas height in px (default 32)
 *  - className    : extra CSS class
 */
export default function AudioWaveform({
  analyserNode,
  active = false,
  color = '#ff7a2f',
  barWidth = 3,
  barGap = 2,
  height = 32,
  className = '',
}) {
  const canvasRef = useRef(null);
  const rafRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !analyserNode || !active) return;

    const ctx = canvas.getContext('2d');
    const bufferLength = analyserNode.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    const draw = () => {
      rafRef.current = requestAnimationFrame(draw);

      // Resize canvas to match container width (CSS px -> device px)
      const rect = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      const w = rect.width * dpr;
      const h = rect.height * dpr;
      if (canvas.width !== w || canvas.height !== h) {
        canvas.width = w;
        canvas.height = h;
      }

      analyserNode.getByteFrequencyData(dataArray);

      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const totalBarWidth = (barWidth + barGap) * dpr;
      const barCount = Math.floor(canvas.width / totalBarWidth);
      // Sample evenly across the frequency spectrum
      const step = Math.max(1, Math.floor(bufferLength / barCount));

      for (let i = 0; i < barCount; i++) {
        const value = dataArray[i * step] || 0;
        const percent = value / 255;
        const barH = Math.max(2 * dpr, percent * canvas.height * 0.9);
        const x = i * totalBarWidth;
        const y = (canvas.height - barH) / 2;

        ctx.fillStyle = color;
        ctx.beginPath();
        if (ctx.roundRect) {
          ctx.roundRect(x, y, barWidth * dpr, barH, 1.5 * dpr);
        } else {
          ctx.rect(x, y, barWidth * dpr, barH);
        }
        ctx.fill();
      }
    };

    draw();

    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [analyserNode, active, color, barWidth, barGap]);

  return (
    <canvas
      ref={canvasRef}
      className={`audio-waveform ${className}`}
      style={{ height: `${height}px` }}
    />
  );
}
