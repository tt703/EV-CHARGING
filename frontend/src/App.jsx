import { useEffect, useState } from 'react';
import Login from './Login';

function App() {
  const [chargers, setChargers] = useState([]);
  const [stats, setStats] = useState({ revenue: 0, energy: 0 });
  const [token, setToken] = useState(localStorage.getItem('adminToken'));

  // Modal States
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newChargerId, setNewChargerId] = useState('');
  
  // History Modal States
  const [isHistoryModalOpen, setIsHistoryModalOpen] = useState(false);
  const [chargerHistory, setChargerHistory] = useState([]);
  const [activeHistoryId, setActiveHistoryId] = useState('');

  // Force login if no token exists
  if (!token) {
    return <Login setToken={setToken} />;
  }

  // Handle auto-logout function
  const logout = () => {
    setToken(null);
    localStorage.removeItem('adminToken');
  };

  const fetchChargers = () => {
    if (!token) return; 

    fetch('http://localhost:8000/api/chargers', {
      headers: {
        'Authorization': `Bearer ${token}` 
      }
    })
      .then(res => {
        if (res.status === 401) {
          logout();
          throw new Error("Token rejected by Python!");
        }
        return res.json();
      })
      .then(data => {
        setChargers(data.chargers || []);
        setStats({ revenue: data.revenue || 0, energy: data.energy || 0 });
      })
      .catch(err => console.error("Fetch Error Caught:", err));
  };

  useEffect(() => {
    fetchChargers();
  }, [token]);

  const handleCommand = (id, action) => {
    fetch(`http://localhost:8000/api/command/${id}/${action}`, { 
        method: 'POST',
        headers: { 
            'Authorization': `Bearer ${token}` 
        } 
    })
      .then(res => {
        if (res.status === 401) {
          logout();
        } else {
          fetchChargers(); 
        }
      });
  };

  const handleAddCharger = async (e) => {
    e.preventDefault();
    if (!newChargerId) return;

    try {
      const response = await fetch('http://localhost:8000/api/chargers', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}` 
        },
        body: JSON.stringify({ charger_id: newChargerId })
      });

      if (response.ok) {
        setIsModalOpen(false); 
        setNewChargerId('');   
        fetchChargers();       
      } else {
        alert("Failed to add charger. It might already exist in the database!");
      }
    } catch (error) {
      console.error("Error adding charger:", error);
    }
  };

  const handleDeleteCharger = async (id) => {
    if (!window.confirm(`Are you sure you want to permanently delete ${id}?`)) return;

    try {
      const response = await fetch(`http://localhost:8000/api/chargers/${id}`,{
        method: 'DELETE',
        headers: {'Authorization' : `Bearer ${token}`}
      });

      if (response.ok){
        fetchChargers();
      } else {
        alert("Cannot delete charger. It might have active sessions!");
      }
    } catch (error) {
      console.error("Error deleting charger: ", error);
    }
  };

  const handleViewHistory = async (id) => {
    try {
      // FIX: URL updated to plural "chargers" to match Python endpoint!
      const response = await fetch(`http://localhost:8000/api/chargers/${id}/history`,{
        headers: { 'Authorization': `Bearer ${token}`}
      });

      if (response.ok){
        const data = await response.json();
        setChargerHistory(data.history || []);
        setActiveHistoryId(id);
        setIsHistoryModalOpen(true);
      }
    } catch (error){
      console.error("Error fetching history: ", error);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-950 via-teal-900 to-black text-white p-6 md:p-10 font-sans relative overflow-x-hidden">
      
      {/* Decorative background blobs */}
      <div className="absolute top-20 left-20 w-72 h-72 md:w-96 md:h-96 bg-green-500 rounded-full mix-blend-multiply filter blur-[100px] opacity-40 pointer-events-none z-0"></div>
      <div className="absolute bottom-20 right-20 w-72 h-72 md:w-96 md:h-96 bg-teal-500 rounded-full mix-blend-multiply filter blur-[100px] opacity-40 pointer-events-none z-0"></div>

      <div className="relative z-10 max-w-6xl mx-auto w-full">
        {/* Header with Add Charger & Logout Buttons */}
        <div className="flex flex-col md:flex-row justify-between items-center mb-8 md:mb-12 gap-4">
            <h1 className="text-3xl md:text-5xl font-extrabold tracking-tight text-center md:text-left">
            myCharger <span className="text-green-400 drop-shadow-lg">EV Center</span>
            </h1>
            <div className="flex gap-4">
              <button 
                onClick={() => setIsModalOpen(true)} 
                className="bg-green-500 hover:bg-green-400 text-white py-2 px-4 rounded-xl text-sm font-semibold shadow-[0_0_15px_rgba(34,197,94,0.4)] transition"
              >
                + Add Charger
              </button>
              <button 
                  onClick={logout} 
                  className="bg-red-500/80 hover:bg-red-500 text-white py-2 px-4 rounded-xl text-sm font-semibold transition shadow-lg"
              >
                  Logout
              </button>
            </div>
        </div>
        
        {/* Glassmorphism Stats Panel */}
        <div className="bg-white/10 backdrop-blur-xl border border-white/20 shadow-2xl rounded-3xl p-6 md:p-8 mb-10 flex flex-col sm:flex-row gap-6 sm:gap-16 items-start sm:items-center w-full">
          <div className="w-full sm:w-auto">
            <p className="text-green-200 text-xs md:text-sm font-medium uppercase tracking-widest mb-1">Total Revenue</p>
            <p className="text-3xl md:text-4xl font-bold truncate">R {stats.revenue}</p>
          </div>
          <div className="w-full sm:w-auto">
            <p className="text-green-200 text-xs md:text-sm font-medium uppercase tracking-widest mb-1">Energy Delivered</p>
            <p className="text-3xl md:text-4xl font-bold truncate">{stats.energy} kWh</p>
          </div>
        </div>

        {/* Chargers Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 md:gap-8 w-full">
          {chargers.map(c => (
            <div key={c.charger_id} className="bg-white/5 backdrop-blur-lg border border-white/10 shadow-xl rounded-3xl p-6 flex flex-col hover:bg-white/10 transition duration-300 h-full w-full relative">
              
              {/* Delete Button (FIXED: absolute) */}
              <button onClick={() => handleDeleteCharger(c.charger_id)}
                className="absolute top-4 right-4 text-red-400 hover:text-red-500 font-bold text-lg bg-red-400/10 hover:bg-red-500/20 w-8 h-8 rounded-full flex items-center justify-center transition"
                title="Delete Charger">
                ×
              </button>

              <div className="flex justify-between items-start mb-6 gap-2 pr-8">
                <h3 className="text-xl md:text-2xl font-semibold tracking-wide truncate" title={c.charger_id}>{c.charger_id}</h3>
              </div>
              
              <div className="mb-6">
                <span className={`px-3 py-1 rounded-full text-[10px] md:text-xs font-bold tracking-wider whitespace-nowrap ${
                  c.status === 'CHARGING' 
                    ? 'bg-yellow-400/20 text-yellow-300 border border-yellow-400/30 shadow-[0_0_15px_rgba(250,204,21,0.3)]' 
                    : 'bg-green-400/20 text-green-300 border border-green-400/30'
                }`}>
                  {c.status}
                </span>
              </div>
              
              <div className="mt-auto flex flex-col gap-3 w-full">
                <div className="flex gap-3 sm:gap-4 w-full">
                  <button 
                    onClick={() => handleCommand(c.charger_id, 'start')} 
                    className="flex-1 bg-green-500/80 hover:bg-green-500 text-white py-2 rounded-xl text-sm font-semibold transition shadow-[0_0_20px_rgba(34,197,94,0.4)] hover:shadow-[0_0_25px_rgba(34,197,94,0.6)]"
                  >
                    Start
                  </button>
                  <button 
                    onClick={() => handleCommand(c.charger_id, 'stop')} 
                    className="flex-1 bg-white/5 hover:bg-white/10 text-white py-2 rounded-xl text-sm font-semibold transition border border-white/10 backdrop-blur-sm"
                  >
                    Stop
                  </button>
                </div>
                {/* FIX: Changed lowercase onclick to onClick */}
                <button
                  onClick={() => handleViewHistory(c.charger_id)}
                  className="w-full bg-blue-500/20 hover:bg-blue-500/40 text-blue-300 border border-blue-500/30 py-2 rounded-xl text-sm font-semibold transition">
                  View History
                </button>
              </div>

            </div>
          ))}
        </div>
      </div>

      {/* --- ADD CHARGER MODAL --- */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex justify-center items-center p-4">
          <div className="bg-[#1e1e2f] border border-white/10 p-8 rounded-3xl shadow-2xl w-full max-w-md">
            <h2 className="text-2xl font-bold mb-6 text-white">Register New Charger</h2>
            <form onSubmit={handleAddCharger} className="flex flex-col gap-4">
              <input 
                type="text" 
                placeholder="e.g. ZA-ABB-002" 
                value={newChargerId}
                onChange={(e) => setNewChargerId(e.target.value)}
                className="bg-white/5 border border-white/20 text-white rounded-xl p-3 focus:outline-none focus:border-green-400 transition"
                required
              />
              <div className="flex gap-4 mt-4">
                <button 
                  type="button" 
                  onClick={() => setIsModalOpen(false)} 
                  className="flex-1 bg-white/10 hover:bg-white/20 py-3 rounded-xl font-semibold transition text-sm"
                >
                  Cancel
                </button>
                <button 
                  type="submit" 
                  className="flex-1 bg-green-500 hover:bg-green-400 py-3 rounded-xl font-semibold shadow-[0_0_15px_rgba(34,197,94,0.4)] transition text-sm"
                >
                  Save Charger
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* --- HISTORY MODAL --- */}
      {isHistoryModalOpen && (
        <div className="fixed inset-0 bg-white/70 backdrop-blur-sm z-50 flex justify-center items-center p-4">
          <div className="bg-[#1e1e2f] border border-white/10 p-6 md:p-8 rounded-3xl shadow-2xl w-full max-w-2xl max-h-[80vh] flex flex-col">
           <div className="flex justify-between items-center mb-6">
            <h2 className="text-xl md:text-2xl font-bold text-white">History: {activeHistoryId}</h2>
            <button onClick={() => setIsHistoryModalOpen(false)} className="text-gray-400 hover:text-white text-2xl font-bold">×</button>
           </div>
           <div className="overflow-y-auto overflow-x-auto pr-2">
             <table className="w-full text-left text-sm text-gray-300">
               <thead className="bg-white/5 text-xs uppercase text-gray-400 sticky top-0">
                 <tr>
                   <th className="px-4 py-3 rounded-tl-lg">Phone</th>
                   <th className="px-4 py-3">Start Time</th>
                   <th className="px-4 py-3">Energy</th>
                   <th className="px-4 py-3 rounded-tr-lg">Status</th>
                 </tr>
               </thead>
             <tbody>
              {chargerHistory.length === 0 ? (
                <tr>
                  <td colSpan="4" className="text-center py-6 text-gray-500">No charging history found.</td>
                </tr>
              ) : (
                chargerHistory.map((session, idx) => (
                  <tr key={idx} className="border-b border-white/5 hover:bg-white/5 transition">
                    <td className="px-4 py-3 font-medium text-white">{session.user_phone}</td>
                    <td className="px-4 py-3">{new Date(session.start_time).toLocaleString()}</td>
                    <td className="px-4 py-3 text-green-400 font-semibold">{session.kwh_delivered || 0} kWh</td>
                    <td className="px-4 py-3">
                       <span className={`px-2 py-1 rounded text-[10px] font-bold ${session.status === 'COMPLETED' ? 'bg-green-500/20 text-green-300' : 'bg-yellow-500/20 text-yellow-300'}`}>
                         {session.status}
                       </span>
                    </td>
                  </tr>
                ))
              )}
             </tbody>
             </table>
           </div>
           <button onClick={() => setIsHistoryModalOpen(false)}
            className="mt-6 w-full bg-white/10 hover:bg-white/20 py-3 rounded-xl font-semibold transition text-sm">
            Close
           </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;