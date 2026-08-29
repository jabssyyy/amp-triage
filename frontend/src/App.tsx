import { BrowserRouter, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import { StoreProvider } from "./store";
import Overview from "./pages/Overview";
import Shortlist from "./pages/Shortlist";
import History from "./pages/History";
import Candidate from "./pages/Candidate";
import Compare from "./pages/Compare";
import WhatIf from "./pages/WhatIf";
import Evidence from "./pages/Evidence";
import Graph from "./pages/Graph";
import Validation from "./pages/Validation";
import Projects from "./pages/Projects";
import Login from "./pages/Login";

import Analytics from "./pages/Analytics";

export default function App() {
  return (
    <BrowserRouter>
      <StoreProvider>
        <Layout>
          <Routes>
            <Route path="/" element={<Overview />} />
            <Route path="/shortlist" element={<Shortlist />} />
            <Route path="/history" element={<History />} />
            <Route path="/candidate" element={<Candidate />} />
            <Route path="/compare" element={<Compare />} />
            <Route path="/whatif" element={<WhatIf />} />
            <Route path="/evidence" element={<Evidence />} />
            <Route path="/graph" element={<Graph />} />
            <Route path="/validation" element={<Validation />} />
            <Route path="/projects" element={<Projects />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/login" element={<Login />} />
          </Routes>
        </Layout>
      </StoreProvider>
    </BrowserRouter>
  );
}

