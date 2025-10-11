import React, { useEffect, useState, useRef } from 'react';
import { ToolCallEvent } from './chatApi';
import './ToolCallStatus.css';

interface ToolCallStatusProps {
  currentTool: ToolCallEvent | null;
  isActive: boolean;
}

// Progressive status messages for simulated progress (Option B)
const SIMULATED_MESSAGES = [
  { delay: 0, text: '🎵 Analyzing your request...' },
  { delay: 5000, text: '🔍 Finding the perfect tracks...' },
  { delay: 13000, text: '✨ Curating your playlist...' },
  { delay: 21000, text: '🎧 Almost there...' }
];

const ToolCallStatus: React.FC<ToolCallStatusProps> = ({ currentTool, isActive }) => {
  const [visible, setVisible] = useState(false);
  const [displayMessage, setDisplayMessage] = useState<string>('');
  const timersRef = useRef<Array<ReturnType<typeof setTimeout>>>([]);

  useEffect(() => {
    // Clear any existing timers
    const clearTimers = () => {
      timersRef.current.forEach(timer => clearTimeout(timer));
      timersRef.current = [];
    };

    if (isActive) {
      setVisible(true);

      // If we have a real tool event (from streaming - Option A), use it
      if (currentTool && currentTool.message) {
        clearTimers();
        setDisplayMessage(currentTool.message);
      } else {
        // Otherwise, simulate progress with timed messages (Option B)
        clearTimers();

        SIMULATED_MESSAGES.forEach(({ delay, text }) => {
          const timer = setTimeout(() => {
            setDisplayMessage(text);
          }, delay);
          timersRef.current.push(timer);
        });
      }
    } else {
      // When loading completes, clear timers and fade out
      clearTimers();
      const fadeTimer = setTimeout(() => {
        setVisible(false);
      }, 300);
      timersRef.current.push(fadeTimer);
    }

    // Cleanup on unmount
    return () => clearTimers();
  }, [currentTool, isActive]);

  if (!visible && !isActive) {
    return null;
  }

  return (
    <div
      className={`tool-call-status-inline ${isActive ? 'active' : 'inactive'}`}
      aria-live="polite"
    >
      <div className="tool-call-inline-card">
        <div className="tool-call-spinner">
          <div className="spinner-dot"></div>
          <div className="spinner-dot"></div>
          <div className="spinner-dot"></div>
        </div>
        <span className="tool-call-message">{displayMessage}</span>
      </div>
    </div>
  );
};

export default ToolCallStatus;
