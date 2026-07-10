import { BrowserRouter, Route, Routes } from "react-router-dom";
import { SessionProvider } from "./session";
import { Layout } from "./components/Layout";
import { RankedList } from "./components/RankedList";
import { InfluencerDetail } from "./components/InfluencerDetail";
import { Compare } from "./components/Compare";

export default function App() {
  return (
    <SessionProvider>
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<RankedList />} />
            <Route path="/influencers/:id" element={<InfluencerDetail />} />
            <Route path="/compare" element={<Compare />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </SessionProvider>
  );
}
