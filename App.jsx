import { useState } from 'react';
import { jsPDF } from 'jspdf';
import './index.css';

function App() {
  const [url, setUrl] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const analyzeRepo = async () => {
    setLoading(true);
    try {
      const res = await fetch('http://127.0.0.1:8000/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
      });
      const data = await res.json();
      setResult(data);
    } catch (err) {
      console.error("Error analyzing repo:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleBack = () => {
    setResult(null);
    setUrl('');
  };

  const downloadPDF = () => {
    if (!result) return;
    const doc = new jsPDF();
    doc.setFontSize(16);
    doc.text("Repository Mirror Report", 20, 20);

    doc.setFontSize(12);
    doc.text(`Score: ${result.score.total} (${result.tier.tier} Tier)`, 20, 40);
    doc.text(`Summary: ${result.summary}`, 20, 55);

    doc.text("Roadmap:", 20, 70);
    result.roadmap.forEach((item, i) => {
    doc.text(`- ${item}`, 25, 80 + i * 10);
  });

    doc.save("repo-analysis.pdf");
  };

  return (
    <div className="app-container">
      <h1 className="app-title">🔍 Repository Mirror</h1>

      {!result && (
        <div className="input-group">
          <input
            value={url}
            onChange={e => setUrl(e.target.value)}
            placeholder="Enter GitHub repo URL"
            className="input-field"
          />
          <button onClick={analyzeRepo} disabled={loading} className="btn-primary">
            {loading ? "Analyzing..." : "Analyze"}
          </button>
        </div>
      )}

      {result && result.error && (
        <div className="error-box">
          ❌ <strong>Error:</strong> {result.error}
        </div>
      )}

      {result && result.score && result.tier && (
        <div className="result-card">
          <h2 className="score-heading">
            Score: {result.score.total}
            <span className={`badge ${result.tier.tier.toLowerCase()}`}>
              {result.tier.badge} {result.tier.tier}
            </span>
          </h2>
          <p className="summary"><strong>Summary:</strong> {result.summary}</p>
          <h3 className="roadmap-title">🛠 Roadmap</h3>
          <ul className="roadmap-list">
            {result.roadmap.map((item, i) => <li key={i}>{item}</li>)}
          </ul>

          <div className="button-group">
            <button onClick={handleBack} className="btn-secondary">⬅ Back</button>
            <button onClick={downloadPDF} className="btn-download">📄 Download PDF</button>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
