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

function ReadinessChart({ features }) {
  const data = {
    labels: features.map((feature) => feature.feature_name),
    datasets: [
      {
        label: "Readiness Score",
        data: [100, 100, 100, 75, 100],
        backgroundColor: [
          "#4CAF50",
          "#4CAF50",
          "#4CAF50",
          "#FF9800",
          "#4CAF50",
        ],
        borderRadius: 8,
      },
    ],
  };

  const options = {
    responsive: true,
    plugins: {
      legend: {
        position: "top",
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        max: 100,
      },
    },
  };

  return <Bar data={data} options={options} />;
}

export default ReadinessChart;