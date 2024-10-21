import React from 'react'
import mm from 'images/mm.png'
import morgan from 'images/morgan.png'

export const Header = ({ isAuthenticated, setIsAuthenticated }) => {
  const handleLogout = () => {
    localStorage.removeItem('authToken')
    setIsAuthenticated(false)
  }

  return (
    <div className="flex flex-row justify-between items-center px-8 py-3.5 bg-black w-full">
      <div className="pr-8 border-r border-ink">
        <a href="/">
          <img width={118} height={30} src={mm} alt="Logo" />
        </a>
      </div>
      <div className="flex-grow flex justify-center">
        <img width={236} height={30} src={morgan} alt="Logo" className="max-w-full" />
      </div>
      {isAuthenticated && (
        <div className="ml-auto">
          <button 
            onClick={handleLogout} 
            className="bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-4 rounded-full transition duration-300 ease-in-out transform hover:scale-105 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-opacity-50"
          >
            Logout
          </button>
        </div>
      )}
    </div>
  )
}