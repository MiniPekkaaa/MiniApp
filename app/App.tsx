import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import MainMenu from './components/MainMenu';
import OrderType from './components/OrderType';
import ManualOrder from './components/ManualOrder';

const App = () => {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<MainMenu />} />
        <Route path="/order-type" element={<OrderType />} />
        <Route path="/manual-order" element={<ManualOrder />} />
      </Routes>
    </Router>
  );
};

export default App; 