import React, { useState, useEffect } from "react";
import "./HospitalDashboard.css"; 

const HospitalDashboard = () => {
  const [data, setData] = useState([]);
  const [selectedState, setSelectedState] = useState("AK");

  useEffect(() => {
    fetch("/data/top_hospitals.json")
      .then((response) => response.json())
      .then((data) => setData(data));
  }, []);

  const states = [...new Set(data.map((item) => item.State))];
  const topHospitals = data.filter((hospital) => hospital.State === selectedState).slice(0, 10);;

  return (
    <div className="dashboard-container">
      <h1>Top Hospitals by State</h1>
      <select
        onChange={(e) => setSelectedState(e.target.value)}
        className="state-dropdown"
      >
        {states.map((state) => (
          <option key={state} value={state}>
            {state}
          </option>
        ))}
      </select>
      <table className="hospital-table">
        <thead>
          <tr>
            <th>Hospital Name</th>
            <th>Rating</th>
          </tr>
        </thead>
        <tbody>
          {topHospitals.map((hospital, index) => (
            <tr key={index}>
              <td>{hospital["Hospital Name"]}</td>
              <td>{hospital["Hospital overall rating"]}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default HospitalDashboard;
