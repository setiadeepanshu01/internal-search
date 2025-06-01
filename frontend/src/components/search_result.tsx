import React, { useEffect, useRef, useState } from 'react'
import { SourceIcon } from './source_icon'
import { SourceType } from '../types'
import { ReactComponent as ArrowDown } from 'images/chevron_down_icon.svg'

interface SearchResultProps extends SourceType {
  toggleSource: (source: string) => void
}

const TITLE_HEIGHT = 59

const formatPath = (url: string) => {
  const parsedUrl = new URL(url);
  const path = decodeURIComponent(parsedUrl.pathname);
  const parts = path.split('/').filter(Boolean);
  
  // Start from the second part (index 1) if it exists
  const pathParts = parts.length > 1 ? parts.slice(1, -1) : parts.slice(0, -1);
  
  // Remove unwanted punctuation including backticks and trim whitespace
  const cleanParts = pathParts.map(part => part.replace(/['"`]/g, '').trim());
  
  const formattedPath = cleanParts.join(' > ');
  
  // Split the path into two lines if it's longer than 50 characters
  if (formattedPath.length > 50) {
    const midPoint = Math.floor(formattedPath.length / 2);
    const splitIndex = formattedPath.indexOf(' > ', midPoint);
    if (splitIndex !== -1) {
      return [
        formattedPath.slice(0, splitIndex),
        formattedPath.slice(splitIndex + 3)
      ];
    }
  }
  
  return [formattedPath];
};

const extractPathUrl = (url: string) => {
  try {
    const parsedUrl = new URL(url);
    const path = decodeURIComponent(parsedUrl.pathname);
    const parts = path.split('/').filter(Boolean);
    
    if (parts.length > 1) {
      const pathUrlParts = parts.slice(0, -1).join('/');
      return `${parsedUrl.origin}/${pathUrlParts}`;
    }
  } catch (error) {
    console.error('Invalid URL', error);
  }
  return null;
};

export const SearchResult: React.FC<SearchResultProps> = ({
  name,
  icon,
  url,
  summary,
  updated_at,
  confidence,
  expanded,
  toggleSource,
}) => {
  const ref = useRef<HTMLDivElement>(null)
  const [blockHeight, setBlockHeight] = useState<string | number>(0)

  // Prevent expand when click is on link
  const onToggle = (event) => !event.target.href && toggleSource(name)

  useEffect(() => {
    const blockHeight = ref.current?.clientHeight

    if (blockHeight) {
      setBlockHeight(blockHeight)
    }
  }, [summary])

  const updatedAtDate = new Date(updated_at || '')
  const pathUrl = extractPathUrl(url);

  return (
    <div className="flex flex-col">
      <div
        className="ease-in duration-300 overflow-hidden bg-gray-50 rounded-md shadow-md hover:-translate-y-1 hover:shadow-lg"
        style={{ height: `${expanded ? blockHeight : TITLE_HEIGHT}px` }}
      >
        <div
          className="p-4 grid grid-cols-1 gap-2 items-start overflow-hidden"
          data-source={name}
          ref={ref}
        >
          <div 
            onClick={onToggle}
            className="flex items-center gap-4 justify-between overflow-hidden cursor-pointer hover:bg-gray-100 rounded px-2 py-1 -mx-2 -my-1"
          >
            <div className="flex items-center gap-3">
              <SourceIcon
                className="rounded-md flex justify-center px-2 py-1 text-slate-400 text-xs flex-shrink-0"
                icon={icon}
              />
              <h4 className="flex flex-row space-x-1.5 pb-2 text-md mb-1 font-semibold overflow-ellipsis overflow-hidden whitespace-nowrap text-blue-500 text-lg">
                {name}
              </h4>
            </div>
            <ArrowDown
              className={`ease-in duration-300 flex-shrink-0 ${
                expanded ? 'rotate-180' : 'rotate-0'
              }`}
            />
          </div>
          <div className="grid grid-cols-[auto_1fr] gap-2 items-start ml-2">
          <span className="rounded-md flex justify-center px-2 py-1 text-slate-400 text-xs">
            URL
          </span>
          <a
            className="hover:text-blue-800 text-blue-500 text-sm overflow-ellipsis overflow-hidden whitespace-nowrap"
            target="_blank"
            rel="noreferrer"
            href={url}
          >
            {url}
          </a>
          <span className="rounded-md flex justify-center px-2 py-1 text-slate-400 text-xs">
            PATH
          </span>
          {pathUrl && (
            <a
              className="hover:text-blue-800 text-blue-500 text-sm overflow-ellipsis overflow-hidden whitespace-nowrap"
              target="_blank"
              rel="noreferrer"
              href={pathUrl}
            >
              {formatPath(url).join(' ')}
            </a>
          )}
          {Array.isArray(summary) ? summary.map((text, index) => (
            <React.Fragment key={index}>
              <span className="rounded-md flex justify-center px-2 py-1 text-slate-400 text-xs">
                Summary
              </span>
              <p className="text-sm mb-2 overflow-ellipsis text-black">
                {text}
              </p>
            </React.Fragment>
          )) : summary && (
            <React.Fragment>
              <span className="rounded-md flex justify-center px-2 py-1 text-slate-400 text-xs">
                Summary
              </span>
              <p className="text-sm mb-2 overflow-ellipsis text-black">
                {summary}
              </p>
            </React.Fragment>
          )}
          </div>
        </div>
      </div>
      <div className="flex justify-between items-center mt-1">
        {confidence && (
          <span className="text-zinc-400 text-xs tracking-tight font-medium">
            Confidence Score: {confidence.toFixed(1)}%
          </span>
        )}
        {updated_at && (
          <span className="text-zinc-400 text-xs tracking-tight font-medium uppercase">
            {`LAST UPDATED ${updatedAtDate.toLocaleDateString('common', {
              month: 'short',
            })} ${updatedAtDate.toLocaleDateString('common', {
              day: 'numeric',
            })}, ${updatedAtDate.getFullYear()}`}
          </span>
        )}
      </div>
    </div>
  )
}
