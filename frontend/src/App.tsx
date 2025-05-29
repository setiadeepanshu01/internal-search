import React, { useState, useEffect } from 'react'
import {
  actions,
  AppStatus,
  thunkActions,
  useAppDispatch,
  useAppSelector,
} from 'store/provider'
import { Header } from 'components/header'
import { Chat } from 'components/chat/chat'
import SearchInput from 'components/search_input'
import { ReactComponent as ChatIcon } from 'images/chat_icon.svg'
import { ReactComponent as MX2Logo } from 'images/mx2_logo.svg'
import { SearchResults } from './components/search_results'
import { Loader } from 'components/loader'
import LoginForm from 'components/login_form'

// Animated loading text component
const AnimatedLoadingText: React.FC = () => {
  const [dots, setDots] = useState('')
  const [textIndex, setTextIndex] = useState(0)

  const loadingTexts = [
    'Searching documents',
    'Reviewing sources',
    'Analyzing content',
    'Gathering insights',
    'Almost ready'
  ]

  useEffect(() => {
    const dotsInterval = setInterval(() => {
      setDots(prev => {
        if (prev === '...') return '.'
        return prev + '.'
      })
    }, 500) // Change dots every 500ms

    const textInterval = setInterval(() => {
      setTextIndex(prev => (prev + 1) % loadingTexts.length)
    }, 2000) // Change text every 2 seconds

    return () => {
      clearInterval(dotsInterval)
      clearInterval(textInterval)
    }
  }, [])

  return (
    <span>
      {loadingTexts[textIndex]}{dots}
    </span>
  )
}

const App = () => {
  const dispatch = useAppDispatch()
  const status = useAppSelector((state) => state.status)
  const sources = useAppSelector((state) => state.sources)
  const [summary, ...messages] = useAppSelector((state) => state.conversation)
  const hasSummary = useAppSelector(
    (state) => !!state.conversation?.[0]?.content
  )
  const [searchQuery, setSearchQuery] = useState<string>('')
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    checkAuthStatus()
  }, [])

  const checkAuthStatus = () => {
    const token = localStorage.getItem('authToken')
    setIsAuthenticated(!!token)
    setIsLoading(false)
  }

  const handleSearch = (query: string) => {
    dispatch(thunkActions.search(query))
  }
  const handleSendChatMessage = (query: string) => {
    dispatch(thunkActions.askQuestion(query))
  }
  const handleAbortRequest = () => {
    dispatch(thunkActions.abortRequest())
  }
  const handleToggleSource = (name: string) => {
    dispatch(actions.sourceToggle({ name }))
  }
  const handleSourceClick = (name: string) => {
    dispatch(actions.sourceToggle({ name, expanded: true }))

    setTimeout(() => {
      document
        .querySelector(`[data-source="${name}"]`)
        ?.scrollIntoView({ behavior: 'smooth' })
    }, 300)
  }

  const handleRetry = () => {
    if (searchQuery) {
      dispatch(thunkActions.search(searchQuery))
    }
  }

  const handleClear = () => {
    dispatch(actions.reset())
    setSearchQuery('')
  }

  const suggestedQueries = [
    'Can you explain what a skeletal injury is in legal terms?',
    'What does ATD stand for in a legal context?',
    'What is general liability insurance and what does it cover?',
    'What qualifies a lawsuit as a class action?',
    'What constitutes proper initial treatment in a personal injury case?',
    'What is negligent security, and when can you sue for it?',
  ]

  if (isLoading) {
    return <Loader />
  }

  return (
    <>
      <Header isAuthenticated={isAuthenticated} setIsAuthenticated={setIsAuthenticated} />
      {isAuthenticated ? (
        <div className="p-4 max-w-2xl mx-auto">
          <SearchInput
            onSearch={handleSearch}
            value={searchQuery}
            appStatus={status}
            onRetry={handleRetry}
            onClear={handleClear}
          />

          {status === AppStatus.Idle ? (
            <div className="mx-auto my-6">
              <h2 className="text-zinc-400 text-sm font-medium mb-3  inline-flex items-center gap-2">
                <ChatIcon /> Common questions
              </h2>
              <div className="flex flex-col space-y-4">
                {suggestedQueries.map((query) => (
                  <button
                    key={query}
                    className="hover:-translate-y-1 hover:shadow-lg hover:bg-zinc-300 transition-transform h-12 px-4 py-2 bg-zinc-200 rounded-md shadow flex items-center text-zinc-700 text-left"
                    onClick={(e) => {
                      e.preventDefault()
                      setSearchQuery(query)
                      handleSearch(query)
                    }}
                  >
                    {query}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <>
              {hasSummary ? (
                <div className="max-w-2xl mx-auto relative">
                  <Chat
                    status={status}
                    messages={messages}
                    summary={summary}
                    onSend={handleSendChatMessage}
                    onAbortRequest={handleAbortRequest}
                    onSourceClick={handleSourceClick}
                  />

                  <SearchResults
                    results={sources}
                    toggleSource={handleToggleSource}
                  />
                </div>
              ) : (
                <div className="h-36 p-6 bg-white rounded-md shadow flex flex-col justify-start items-center gap-4 mt-6">
                  <MX2Logo className="w-16 h-16" />
                  <p className="text-center text-zinc-400 text-sm ">
                    <AnimatedLoadingText />
                  </p>
                </div>
              )}
            </>
          )}
        </div>
      ) : (
        <LoginForm setIsAuthenticated={setIsAuthenticated} />
      )}
    </>
  )
}

export default App
