import React from 'react'
import { SourceIcon } from './source_icon'

export type SourceProps = {
  name: string
  icon: string
  confidence?: number
  onSourceClick: (sourceName: string) => void
}

export const SourceItem: React.FC<SourceProps> = ({
  name,
  icon,
  confidence,
  onSourceClick,
}) => (
  <div
    onClick={() => {
      onSourceClick(name)
    }}
    className="hover:text-blue-600 hover:border-blue-500 inline-flex flex-col gap-1 cursor-pointer px-4 py-3 border-2 rounded-md border-blue-300 text-blue-500 font-medium"
  >
    <div className="inline-flex gap-2 items-center">
      <SourceIcon icon={icon} />
      <span>{name}</span>
    </div>
    {confidence && (
      <span className="text-xs text-zinc-400 font-normal">
        Confidence: {confidence.toFixed(1)}%
      </span>
    )}
  </div>
)
