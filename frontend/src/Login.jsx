import React, { useState } from 'react';

export default function Login({ setToken }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleLogin = async (e) => {
    e.preventDefault();
    
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    try {
      const response = await fetch('http://localhost:8000/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData,
      });

      if (response.ok) {
        const data = await response.json();
        localStorage.setItem('adminToken', data.access_token);
        setToken(data.access_token);
      } else {
        setError('Invalid username or password.');
      }
    } catch (err) {
      setError('Failed to connect to the server.');
    }
  };

  return (
    // Added 'flex items-center justify-center' to perfectly center the login box
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-green-950 via-teal-900 to-black text-white p-6 font-sans relative overflow-x-hidden">
      
      {/* Decorative background blobs to match the dashboard */}
      <div className="absolute top-0 left-0 w-72 h-72 bg-green-500 rounded-full mix-blend-multiply filter blur-[100px] opacity-40 pointer-events-none z-0"></div>
      <div className="absolute bottom-0 right-0 w-72 h-72 bg-teal-500 rounded-full mix-blend-multiply filter blur-[100px] opacity-40 pointer-events-none z-0"></div>

      {/* Glassmorphism Card */}
      <div className="bg-white/10 backdrop-blur-xl border border-white/20 shadow-2xl rounded-3xl p-8 md:p-10 w-full max-w-md relative z-10">
        <h2 className="text-3xl md:text-4xl font-extrabold text-center mb-8 tracking-tight">
          myCharger <span className="text-green-400 drop-shadow-lg">Admin</span>
        </h2>
        
        <form onSubmit={handleLogin} className="flex flex-col gap-5">
          <input 
            type="text" 
            placeholder="Username" 
            value={username} 
            onChange={(e) => setUsername(e.target.value)} 
            className="bg-white/5 border border-white/20 text-white rounded-xl p-4 focus:outline-none focus:border-green-400 transition"
            required
          />
          <input 
            type="password" 
            placeholder="Password" 
            value={password} 
            onChange={(e) => setPassword(e.target.value)} 
            className="bg-white/5 border border-white/20 text-white rounded-xl p-4 focus:outline-none focus:border-green-400 transition"
            required
          />
          <button 
            type="submit" 
            className="bg-green-500 hover:bg-green-400 text-white py-4 rounded-xl font-bold text-lg shadow-[0_0_15px_rgba(34,197,94,0.4)] transition mt-2"
          >
            Login
          </button>
        </form>

        {error && (
          <p className="text-red-400 text-center mt-6 font-medium bg-red-500/10 py-2 rounded-lg">
            {error}
          </p>
        )}
      </div>
    </div>
  );
}