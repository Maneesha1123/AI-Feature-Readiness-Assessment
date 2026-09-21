import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";

import { Bar } from "react-chartjs-2";

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

// Shortens long GitHub issue titles so the x-axis stays readable
function shorten(text, max = 28) {
  if (!text) return "";
  return text.length > max ? text.slice(0, max) + "…" : text;
}

function ReadinessChart({ scores }) {
  // scores is an array of { feature_id, feature_name, readiness_score }
  // passed in from App.jsx after it has fetched real readiness data.

  if (!scores || scores.length === 0) {
    return (
      <p style={{ color: "#666", fontStyle: "italic" }}>
        No readiness data loaded yet.
      </p>
    );
  }

  const data = {
    labels: scores.map((s) => shorten(s.feature_name)),
    datasets: [
      {
        label: "Readiness score (%)",
        data: scores.map((s) => s.readiness_score),
        backgroundColor: scores.map((s) => {
          if (s.readiness_score >= 90) return "#2e7d32"; // green
          if (s.readiness_score >= 60) return "#ed6c02"; // orange
          return "#c62828"; // red
        }),
        borderRadius: 6,
      },
    ],
  };

  const options = {
    responsive: true,
    plugins: {
      legend: { position: "top" },
      tooltip: {
        callbacks: {
          // Show the full, untruncated feature name on hover
          title: (items) => scores[items[0].dataIndex].feature_name,
        },
      },
    },
    scales: {
      y: { beginAtZero: true, max: 100 },
      x: { ticks: { maxRotation: 45, minRotation: 45 } },
    },
  };

  return <Bar data={data} options={options} />;
}

export default ReadinessChart;
