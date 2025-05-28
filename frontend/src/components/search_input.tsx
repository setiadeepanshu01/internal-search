import { ChangeEvent, FormEvent, useEffect, useState } from 'react'
import { ReactComponent as RefreshIcon } from 'images/refresh_icon.svg'
import { ReactComponent as SearchIcon } from 'images/search_icon.svg'
import { ReactComponent as ArrowIcon } from 'images/arrow_icon.svg'
import { ReactComponent as StopIcon } from 'images/stop_icon.svg'
import { AppStatus } from 'store/provider'

export default function SearchInput({ onSearch, value, appStatus, onRetry, onClear }) {
  const [query, setQuery] = useState<string>(value)
  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    if (!!query.length) {
      onSearch(query)
    }
  }
  const handleChange = (event: ChangeEvent<HTMLInputElement>) =>
    setQuery(event.target.value)

  useEffect(() => {
    setQuery(value)
  }, [value])

  return (
    <form className="w-full" onSubmit={handleSubmit}>
      <div className="relative mt-1 flex w-full items-center h-14 gap-2">
        <input
          type="search"
          className={`hover:border-blue-500 outline-none focus-visible:border-blue-600 w-full h-14 rounded-md border-2 border-zinc-300 px-3 py-2.5 pl-12 text-base font-medium placeholder-gray-400 ${
            appStatus === AppStatus.Idle ? 'pr-20' : 'pr-24'
          }`}
          value={query}
          onChange={handleChange}
          placeholder="What is on your mind?"
        />
        <span className="pointer-events-none absolute left-4">
          <SearchIcon />
        </span>
        {appStatus === AppStatus.Idle ? (
          <button
            className="hover:bg-blue disabled:bg-blue-400 px-4 py-2 bg-blue-500 rounded flex items-center absolute right-2 z-10"
            type="submit"
            disabled={!query.length}
          >
            <ArrowIcon width={24} height={24} />
          </button>
        ) : (
          <div className="absolute right-2 z-10 flex gap-1">
            <div className="relative group">
              <button
                className="hover:bg-blue-400 hover:text-blue-100 w-10 h-10 bg-blue-100 rounded flex justify-center items-center text-blue-400"
                type="button"
                onClick={onRetry}
              >
                <RefreshIcon width={20} height={20} />
              </button>
              <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-2 py-1 text-xs text-white bg-gray-800 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
                Retry
              </div>
            </div>
            <div className="relative group">
              <button
                className="hover:bg-red-400 hover:text-red-100 w-10 h-10 bg-red-100 rounded flex justify-center items-center text-red-600"
                type="button"
                onClick={onClear}
              >
                <span className="text-lg font-bold leading-none">×</span>
              </button>
              <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-2 py-1 text-xs text-white bg-gray-800 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
                Clear
              </div>
            </div>
          </div>
        )}
      </div>
    </form>
  )
}
