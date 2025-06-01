import React from 'react'
import { SourceIcon } from './source_icon'
import { Loader } from './loader'

export type SourceProps = {
  name: string
  icon: string
  confidence?: number
  loading?: boolean
  enhanced?: boolean
  error?: boolean
  summary?: string
  onSourceClick: (sourceName: string) => void
}

export const SourceItem: React.FC<SourceProps> = ({
  name,
  icon,
  confidence,
  loading = false,
  enhanced = false,
  error = false,
  summary,
  onSourceClick,
}) => {
  const getStateStyles = () => {
    if (error) return 'border-red-300 text-red-500 hover:text-red-600 hover:border-red-500'
    if (loading) return 'border-yellow-300 text-yellow-600 hover:text-yellow-700 hover:border-yellow-500'
    if (enhanced) return 'border-green-300 text-green-600 hover:text-green-700 hover:border-green-500'
    return 'border-blue-300 text-blue-500 hover:text-blue-600 hover:border-blue-500'
  }

  const getStateIndicator = () => {
    if (loading) return <Loader />
    if (error) return <span className="text-xs">⚠️</span>
    if (enhanced) return <span className="text-xs">✓</span>
    return null
  }

  return (
    <div
      onClick={() => {
        onSourceClick(name)
      }}
      className={`inline-flex flex-col gap-1 cursor-pointer px-4 py-3 border-2 rounded-md font-medium transition-colors ${
        getStateStyles()
      }`}
    >
      <div className="inline-flex gap-2 items-center">
        <SourceIcon icon={icon} />
        <span>{name}</span>
        {getStateIndicator()}
      </div>
      {confidence && (
        <span className="text-xs text-zinc-400 font-normal">
          Confidence: {confidence.toFixed(1)}%
        </span>
      )}
      {summary && summary !== "Loading summary..." && (
        <div className="text-xs text-zinc-600 mt-2 leading-relaxed">
          {summary}
        </div>
      )}
      {loading && (
        <span className="text-xs font-normal opacity-75">
          Generating summary...
        </span>
      )}
      {error && (
        <span className="text-xs font-normal opacity-75">
          Summary failed
        </span>
      )}
    </div>
  )
}
