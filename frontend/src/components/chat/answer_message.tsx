import React from 'react';
import ReactMarkdown from 'react-markdown';
import { Sources } from './sources';
import { ChatMessageType } from '../../types';

interface AnswerMessageProps {
  text: ChatMessageType['content'];
  sources: ChatMessageType['sources'];
  onSourceClick: (source: string) => void;
}

export const AnswerMessage: React.FC<AnswerMessageProps> = ({
  text,
  sources,
  onSourceClick,
}) => {
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
        <div className="text-base leading-tight text-gray-800 whitespace-pre-wrap mb-8">
          <ReactMarkdown>{formattedText}</ReactMarkdown>
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