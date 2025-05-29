import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { Sources } from './sources';
import { ChatMessageType } from '../../types';

interface AnswerMessageProps {
  text: ChatMessageType['content'];
  sources: ChatMessageType['sources'];
  traceId?: string;
  onSourceClick: (source: string) => void;
}

export const AnswerMessage: React.FC<AnswerMessageProps> = ({
  text,
  sources,
  traceId,
  onSourceClick,
}) => {
  const [feedbackGiven, setFeedbackGiven] = useState<'up' | 'down' | null>(null);
  const [isSubmittingFeedback, setIsSubmittingFeedback] = useState(false);
  
  const handleFeedback = async (value: number) => {
    if (!traceId || isSubmittingFeedback) return;
    
    setIsSubmittingFeedback(true);
    try {
      const response = await fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          trace_id: traceId, 
          value 
        })
      });
      
      if (response.ok) {
        setFeedbackGiven(value === 1 ? 'up' : 'down');
      } else {
        console.error('Failed to submit feedback');
      }
    } catch (error) {
      console.error('Error submitting feedback:', error);
    } finally {
      setIsSubmittingFeedback(false);
    }
  };

  const formattedText = text.replace(/  /g, '\n &nbsp;');
  return (
    <div className="mb-4">
      <header className="flex flex-row justify-between mb-8">
        <div className="flex flex-row justify-center align-middle items-center">
          <div className="flex flex-col justify-start">
            <h2 className="text-zinc-700 text-2xl font-bold leading-9">
              Answer
            </h2>
            <p className="text-zinc-400 text-sm font-medium">
              Powered by <b>MX2</b>
            </p>
          </div>
        </div>
      </header>

      {text && (
        <div className="text-base leading-tight text-gray-800 whitespace-pre-wrap mb-4">
          <ReactMarkdown>{formattedText}</ReactMarkdown>
        </div>
      )}
      
      {/* Feedback buttons - only show if we have a traceId and text */}
      {traceId && text && (
        <div className="flex items-center gap-2 mb-4">
          <span className="text-sm text-gray-600">Was this helpful?</span>
          <button
            onClick={() => handleFeedback(1)}
            disabled={isSubmittingFeedback || feedbackGiven === 'up'}
            className={`p-2 rounded-md transition-colors ${
              feedbackGiven === 'up'
                ? 'bg-green-100 text-green-600'
                : 'bg-gray-100 hover:bg-green-100 hover:text-green-600 text-gray-600'
            } ${isSubmittingFeedback ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
            title="Thumbs up"
          >
            👍
          </button>
          <button
            onClick={() => handleFeedback(-1)}
            disabled={isSubmittingFeedback || feedbackGiven === 'down'}
            className={`p-2 rounded-md transition-colors ${
              feedbackGiven === 'down'
                ? 'bg-red-100 text-red-600'
                : 'bg-gray-100 hover:bg-red-100 hover:text-red-600 text-gray-600'
            } ${isSubmittingFeedback ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
            title="Thumbs down"
          >
            👎
          </button>
        </div>
      )}
      
      {sources && (
        <Sources
          showDisclaimer
          sources={sources}
          onSourceClick={onSourceClick}
        />
      )}
    </div>
  );
};
