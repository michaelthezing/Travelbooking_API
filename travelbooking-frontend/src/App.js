// travelbooking-frontend/src/App.js
import React from 'react';
import { BrowserRouter as Router, Route, Switch } from 'react-router-dom';
import Register from './components/Register';
import Login from './components/Login';
import BookTrip from './components/BookTrip';
import MakePayment from './components/MakePayment';

function App() {
  return (
    <Router>
      <div>
        <Switch>
          <Route path="/register" component={Register} />
          <Route path="/login" component={Login} />
          <Route path="/book-trip" component={BookTrip} />
          <Route path="/make-payment" component={MakePayment} />
          <Route path="/search-flights" component={SearchFlights} />
        </Switch>
      </div>
    </Router>
  );
}

export default App;
