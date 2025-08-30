import React, { useState, useEffect } from 'react';
import './AnimatedInstructions.css';

interface Step {
  id: number;
  icon: React.ReactNode;
  title: string;
  description: string;
}

const AnimatedInstructions: React.FC = () => {
  const [currentStep, setCurrentStep] = useState(0);
  const [isTransitioning, setIsTransitioning] = useState(false);

  const steps: Step[] = [
    {
      id: 1,
      icon: (
        <svg viewBox="0 0 24 24" fill="currentColor" className="step-icon">
          <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/>
        </svg>
      ),
      title: "Connect with Spotify",
      description: "Link your Spotify account to access your music library"
    },
    {
      id: 2,
      icon: (
        <svg viewBox="0 0 24 24" fill="currentColor" className="step-icon">
          <path d="M12 2C13.1 2 14 2.9 14 4C14 5.1 13.1 6 12 6C10.9 6 10 5.1 10 4C10 2.9 10.9 2 12 2ZM21 9V7L15 1L9 7V9C9 10.1 9.9 11 11 11V16L7.5 17.5C7.1 17.8 6.6 17.9 6.1 17.8L3 17V15H1V19H3V18L6 19C6.8 19.2 7.6 19 8.3 18.5L12 16.8L15.7 18.5C16.4 19 17.2 19.2 18 19L21 18V19H23V15H21V17L17.9 17.8C17.4 17.9 16.9 17.8 16.5 17.5L13 16V11C14.1 11 15 10.1 15 9V7.8L21 9Z"/>
        </svg>
      ),
      title: "Ask AI to Create Playlist", 
      description: "Tell Mr. DJ what kind of playlist you want - any mood, genre, or occasion!"
    },
    {
      id: 3,
      icon: (
        <svg viewBox="0 0 24 24" fill="currentColor" className="step-icon">
          <path d="M19 3H5C3.9 3 3 3.9 3 5V19C3 20.1 3.9 21 5 21H19C20.1 21 21 20.1 21 19V5C21 3.9 20.1 3 19 3ZM19 19H5V5H19V19ZM17 12H15V10H13V12H11V14H13V16H15V14H17V12Z"/>
        </svg>
      ),
      title: "Playlist Added to Your Account!",
      description: "Your custom AI-generated playlist is automatically saved to your Spotify"
    }
  ];

  useEffect(() => {
    const interval = setInterval(() => {
      setIsTransitioning(true);
      
      setTimeout(() => {
        setCurrentStep((prev) => (prev + 1) % steps.length);
        setIsTransitioning(false);
      }, 500); // Half second transition time
      
    }, 3500); // Change step every 3.5 seconds (3s display + 0.5s transition)

    return () => clearInterval(interval);
  }, [steps.length]);

  return (
    <div className="instructions-container">
      <div className="instructions-header">
        <h2>Your AI Playlist Generator</h2>
        <p>Create personalized Spotify playlists with the power of AI</p>
      </div>
      
      <div className="steps-container">
        <div
          key={steps[currentStep].id}
          className={`step step-${currentStep + 1} active ${isTransitioning ? 'transitioning' : 'visible'}`}
        >
          <div className="step-icon-container">
            {steps[currentStep].icon}
          </div>
          <div className="step-content">
            <h3 className="step-title">{steps[currentStep].title}</h3>
            <p className="step-description">{steps[currentStep].description}</p>
          </div>
        </div>
      </div>
      
      <div className="progress-indicators">
        {steps.map((_, index) => (
          <div
            key={index}
            className={`indicator ${index === currentStep ? 'active' : ''}`}
          />
        ))}
      </div>
    </div>
  );
};

export default AnimatedInstructions;