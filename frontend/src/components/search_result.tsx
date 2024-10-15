import React, { useEffect, useRef, useState } from 'react'
import { SourceIcon } from './source_icon'
import { SourceType } from '../types'
import { ReactComponent as ArrowDown } from 'images/chevron_down_icon.svg'

interface SearchResultProps extends SourceType {
  toggleSource: (source: string) => void
}

const TITLE_HEIGHT = 59

const cleanAndTruncateSummary = (summary: string[], maxWords: number): string[] => {
  const cleanText = (text: string): string => {
    return text
      .toLowerCase()
      .replace(/[^\w\s]/g, '') // Remove non-alphanumeric characters except spaces
      .replace(/\d+/g, '')     // Remove numbers
      .replace(/[_\-]+/g, '')  // Remove underscores and dashes
      .replace(/\s+/g, ' ')    // Replace multiple spaces with a single space
      .trim();
  };
  const capitalizeFirstLetter = (text: string): string => {
    return text.charAt(0).toUpperCase() + text.slice(1);
  };

  let totalWords = 0;
  return summary.reduce((acc, text) => {
    if (totalWords < maxWords) {
      const cleanedText = cleanText(text);
      const words = cleanedText.split(' ');
      const remainingWords = maxWords - totalWords;
      const truncatedWords = words.slice(0, remainingWords);
      totalWords += truncatedWords.length;
      if (truncatedWords.length > 0) {
        acc.push(capitalizeFirstLetter(truncatedWords.join(' ')));
      }
    }
    return acc;
  }, [] as string[]);
};

export const SearchResult: React.FC<SearchResultProps> = ({
  name,
  icon,
  url,
  summary,
  updated_at,
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

  return (
    <div className="flex flex-col">
      <div
        onClick={onToggle}
        className="ease-in duration-300 overflow-hidden cursor-pointer bg-gray-50 rounded-md shadow-md hover:-translate-y-1 hover:shadow-lg"
        style={{ height: `${expanded ? blockHeight : TITLE_HEIGHT}px` }}
      >
        <div
          className="p-4 grid grid-cols-[auto_auto] gap-2 items-start overflow-hidden"
          data-source={name}
          ref={ref}
        >
          <SourceIcon
            className="rounded-md flex justify-center px-2 py-1 text-slate-400 text-xs"
            icon={icon}
          />
          <div className="inline-flex gap-4 justify-between overflow-hidden">
            <h4 className="flex flex-row space-x-1.5 pb-2 text-md mb-1 font-semibold overflow-ellipsis overflow-hidden whitespace-nowrap text-blue-500 text-lg">
              {name}
            </h4>
            <ArrowDown
              className={`ease-in duration-300 flex-shrink-0 ${
                expanded ? 'rotate-180' : 'rotate-0'
              }`}
            />
          </div>
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
          {cleanAndTruncateSummary(summary, 150).map((text, index) => (
            <React.Fragment key={index}>
              <span className="rounded-md flex justify-center px-2 py-1 text-slate-400 text-xs">
                Snippet
              </span>
              <p className="text-sm mb-2 overflow-ellipsis text-black">
                ...{text}
              </p>
            </React.Fragment>
          ))}
        </div>
      </div>
      {updated_at && (
        <span className="self-end mt-1 text-zinc-400 text-xs tracking-tight font-medium uppercase">
          {`LAST UPDATED ${updatedAtDate.toLocaleDateString('common', {
            month: 'short',
          })} ${updatedAtDate.toLocaleDateString('common', {
            day: 'numeric',
          })}, ${updatedAtDate.getFullYear()}`}
        </span>
      )}
    </div>
  )
}
