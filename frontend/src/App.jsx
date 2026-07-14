import ReadinessChart from "./components/ReadinessChart";
import { useEffect, useState } from "react";
import axios from "axios";

import {
  Container,
  Typography,
  Card,
  CardContent,
  Button,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  LinearProgress,
  Chip,
  Box,
  List,
  ListItem,
  ListItemText,
  Grid,
} from "@mui/material";

function App() {
  const [features, setFeatures] = useState([]);
  const [selectedFeature, setSelectedFeature] = useState("");
  const [readiness, setReadiness] = useState(null);

  useEffect(() => {
    axios
      .get("http://127.0.0.1:8000/features")
      .then((response) => {
        setFeatures(response.data);
      })
      .catch((error) => console.error(error));
  }, []);

  const checkReadiness = () => {
    if (!selectedFeature) {
      alert("Please select a feature");
      return;
    }

    axios
      .get(`http://127.0.0.1:8000/readiness/${selectedFeature}`)
      .then((response) => {
        setReadiness(response.data);
      })
      .catch((error) => console.error(error));
  };

  const getChipColor = (status) => {
    if (status === "Ready") return "success";
    if (status === "Partially Ready") return "warning";
    return "error";
  };

  return (
    <Container maxWidth="lg" sx={{ mt: 5, mb: 5 }}>

      <Typography variant="h3" align="center" gutterBottom>
        AI-Assisted Feature Readiness Assessment
      </Typography>

      {/* Dashboard Cards */}

      <Grid container spacing={3} sx={{ mb: 4 }}>

        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ bgcolor: "#1976d2", color: "white" }}>
            <CardContent>
              <Typography variant="h6">Total Features</Typography>
              <Typography variant="h3">{features.length}</Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ bgcolor: "#2e7d32", color: "white" }}>
            <CardContent>
              <Typography variant="h6">Ready</Typography>
              <Typography variant="h3">4</Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ bgcolor: "#ed6c02", color: "white" }}>
            <CardContent>
              <Typography variant="h6">Pending</Typography>
              <Typography variant="h3">1</Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ bgcolor: "#6a1b9a", color: "white" }}>
            <CardContent>
              <Typography variant="h6">Average Score</Typography>
              <Typography variant="h3">80%</Typography>
            </CardContent>
          </Card>
        </Grid>

      </Grid>

      {/* Feature Selection */}

      <Card sx={{ mb: 4 }}>
        <CardContent>

          <FormControl fullWidth>

            <InputLabel>Select Feature</InputLabel>

            <Select
              value={selectedFeature}
              label="Select Feature"
              onChange={(e) => setSelectedFeature(e.target.value)}
            >
              {features.map((feature) => (
                <MenuItem
                  key={feature.feature_id}
                  value={feature.feature_id}
                >
                  {feature.feature_name}
                </MenuItem>
              ))}
            </Select>

          </FormControl>

          <Button
            variant="contained"
            fullWidth
            sx={{ mt: 3 }}
            onClick={checkReadiness}
          >
            Assess Readiness
          </Button>

        </CardContent>
      </Card>

      {readiness && (

        <Card>

          <CardContent>

            <Typography variant="h4" gutterBottom>
              {readiness.feature_name}
            </Typography>

            <Typography>
              <b>Feature ID:</b> {readiness.feature_id}
            </Typography>

            <Typography sx={{ mt: 2 }}>
              <b>Status:</b>{" "}
              <Chip
                label={readiness.status}
                color={getChipColor(readiness.status)}
              />
            </Typography>

            <Typography sx={{ mt: 3 }}>
              Readiness Score
            </Typography>

            <LinearProgress
              variant="determinate"
              value={readiness.readiness_score}
              sx={{
                mt: 1,
                height: 12,
                borderRadius: 5,
              }}
            />

            <Typography sx={{ mt: 1 }}>
              {readiness.readiness_score}%
            </Typography>

            <Box sx={{ mt: 4 }}>

              <Typography variant="h6">
                AI Recommendations
              </Typography>

              {readiness.recommendations.length === 0 ? (

                <Typography color="green">
                  ✅ Feature is ready for production.
                </Typography>

              ) : (

                <List>
                  {readiness.recommendations.map((item, index) => (
                    <ListItem key={index}>
                      <ListItemText primary={item} />
                    </ListItem>
                  ))}
                </List>

              )}

            </Box>

          </CardContent>

        </Card>

      )}
<Card sx={{ mt: 4 }}>
  <CardContent>

    <Typography variant="h5" gutterBottom>
      Feature Readiness Overview
    </Typography>

    <ReadinessChart features={features} />

  </CardContent>
</Card>
    </Container>
  );
}

export default App;