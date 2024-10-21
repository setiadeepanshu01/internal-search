import React, { useState } from 'react';

const LoginForm = ({ setIsAuthenticated }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    fetch('/api/verify-credentials', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ username, password }),
    })
    .then(response => response.json())
    .then(data => {
      if (data.authenticated) {
        localStorage.setItem('authToken', data.token);
        setIsAuthenticated(true);
      } else {
        alert('Invalid credentials');
      }
    })
    .catch(error => {
      console.error('Error:', error);
      alert('An error occurred during authentication');
    });
  };

  return (
    <div id="login-form">
      <form onSubmit={handleSubmit}>
        <img src={process.env.PUBLIC_URL + '/mm.png'} alt="Company Logo" className="logo" />
        <input
          type="text"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="Username"
          required
        />
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Password"
          required
        />
        <button type="submit">Login</button>
      </form>
    </div>
  );
};

export default LoginForm;