import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Home from "./components/Home";
import ListeningType from "./components/ListeningType";
import BrandSelect from "./components/BrandSelect";
import ModelSelect from "./components/ModelSelect";
import VolumeSelect from "./components/VolumeSelect.jsx";
import AmbientAnalysis from "./components/AmbientAnalysis.jsx";
import Results from "./components/Results.jsx";
import HowItWorks from "./components/HowItWorks.jsx";
import AboutUs from "./components/AboutUs.jsx";
import Contact from "./components/Contact.jsx";
import Auth from "./components/Auth.jsx";
import Dashboard from "./components/Dashboard.jsx";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/listening-type" element={<ListeningType />} />
        <Route path="/brand" element={<BrandSelect />} />
        <Route path="/model" element={<ModelSelect />} />
        <Route path="/volume" element={<VolumeSelect />} />
        <Route path="/ambient" element={<AmbientAnalysis />} />
        <Route path="/results" element={<Results />} />
        <Route path="/how-it-works" element={<HowItWorks />} />
        <Route path="/about-us" element={<AboutUs />} />
        <Route path="/contact" element={<Contact />} />
        <Route path="/auth" element={<Auth />} />
        <Route path="/dashboard" element={<Dashboard />} />
      </Routes>
    </Layout>
  );
}
