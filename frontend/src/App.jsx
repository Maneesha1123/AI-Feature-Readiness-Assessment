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
  TextField,
  Divider,
  Alert,
  Stack,
} from "@mui/material";

const API = "http://127.0.0.1:8000";

function App() {
  const [features, setFeatures] = useState([]);
  const [selectedFeature, setSelectedFeature] = useState("");
  const [readiness, setReadiness] = useState(null);

  // Real readiness scores for every feature (used by the stat cards and chart)
  const [allScores, setAllScores] = useState([]);

  // AI traceability assessment (RQ2 + RQ3)
  const [assessment, setAssessment] = useState(null);
  const [loadingAssessment, setLoadingAssessment] = useState(false);

  // Accept / Override decisions keyed by ac_id
  const [decisions, setDecisions] = useState({});
  const [reasonDrafts, setReasonDrafts] = useState({});

  // ---- Load features on mount ----
  useEffect(() => {
    axios
      .get(`${API}/features`)
      .then((res) => setFeatures(res.data))
      .catch((err) => console.error(err));
  }, []);

  // ---- Once features are loaded, fetch each one's real readiness ----
  useEffect(() => {
    if (features.length === 0) return;

    Promise.all(
      features.map((f) =>
        axios
          .get(`${API}/readiness/${f.feature_id}`)
          .then((res) => ({
            feature_id: f.feature_id,
            feature_name: f.feature_name,
            readiness_score: res.data.readiness_score ?? 0,
            status: res.data.status ?? "Unknown",
          }))
          .catch(() => ({
            feature_id: f.feature_id,
            feature_name: f.feature_name,
            readiness_score: 0,
            status: "Unknown",
          }))
      )
    ).then(setAllScores);
  }, [features]);

  // ---- Load the AI assessment and any previously recorded decisions ----
  useEffect(() => {
    loadAssessment();
    axios
      .get(`${API}/evaluation/decisions`)
      .then((res) => {
        const map = {};
        res.data.forEach((d) => {
          map[d.ac_id] = d;
        });
        setDecisions(map);
      })
      .catch((err) => console.error(err));
  }, []);

  const loadAssessment = () => {
    setLoadingAssessment(true);
    axios
      .get(`${API}/ai/assessment`)
      .then((res) => setAssessment(res.data))
      .catch((err) => console.error(err))
      .finally(() => setLoadingAssessment(false));
  };

  const checkReadiness = () => {
    if (!selectedFeature) {
      alert("Select a feature first");
      return;
    }
    axios
      .get(`${API}/readiness/${selectedFeature}`)
      .then((res) => setReadiness(res.data))
      .catch((err) => console.error(err));
  };

  // ---- Record an Accept or Override decision ----
  const recordDecision = (acId, tcId, decision, reason = "") => {
    axios
      .post(`${API}/evaluation/decision`, {
        ac_id: acId,
        tc_id: tcId || "none",
        decision,
        reason,
        participant_id: "anonymous",
      })
      .then((res) => {
        setDecisions((prev) => ({ ...prev, [acId]: res.data }));
        setReasonDrafts((prev) => ({ ...prev, [acId]: "" }));
      })
      .catch((err) => console.error(err));
  };

  // ---- Derived real statistics (no hardcoded numbers) ----
  const readyCount = allScores.filter((s) => s.readiness_score >= 90).length;
  const pendingCount = allScores.filter((s) => s.readiness_score < 90).length;
  const averageScore =
    allScores.length > 0
      ? Math.round(
          allScores.reduce((sum, s) => sum + s.readiness_score, 0) /
            allScores.length
        )
      : 0;

  const chipColor = (status) => {
    if (status === "Ready") return "success";
    if (status === "Partially Ready") return "warning";
    return "error";
  };

  const statusColor = (status) => {
    if (!status) return "default";
    if (status.includes("outdated")) return "error";
    if (status.includes("inferred")) return "info";
    if (status.includes("current")) return "success";
    return "default";
  };

  // ---- One reviewable row in the evaluation section ----
  const ReviewRow = ({ acId, tcId, acText, tcText, status, detail, score }) => {
    const existing = decisions[acId];
    const draft = reasonDrafts[acId] ?? "";

    return (
      <Card variant="outlined" sx={{ mb: 2 }}>
        <CardContent>
          <Stack
            direction="row"
            spacing={1}
            alignItems="center"
            sx={{ mb: 1.5, flexWrap: "wrap" }}
          >
            <Chip label={acId} size="small" />
            <Chip label={status} size="small" color={statusColor(status)} />
            {score != null && (
              <Chip
                label={`similarity ${score.toFixed(2)}`}
                size="small"
                variant="outlined"
              />
            )}
          </Stack>

          <Typography variant="body2" color="text.secondary">
            Requirement
          </Typography>
          <Typography sx={{ mb: 1.5 }}>{acText}</Typography>

          <Typography variant="body2" color="text.secondary">
            {tcId ? `Test case ${tcId}` : "Test case"}
          </Typography>
          <Typography sx={{ mb: 1.5 }}>
            {tcText || "No test case proposed."}
          </Typography>

          <Alert severity="info" sx={{ mb: 2 }}>
            {detail}
          </Alert>

          {existing ? (
            <Alert
              severity={existing.decision === "accept" ? "success" : "warning"}
            >
              You {existing.decision === "accept" ? "accepted" : "overrode"} this
              suggestion.
              {existing.reason ? ` Reason: "${existing.reason}"` : ""}
            </Alert>
          ) : (
            <Box>
              <TextField
                fullWidth
                size="small"
                multiline
                minRows={2}
                placeholder="If you override this, briefly say why"
                value={draft}
                onChange={(e) =>
                  setReasonDrafts((prev) => ({
                    ...prev,
                    [acId]: e.target.value,
                  }))
                }
                sx={{ mb: 1.5 }}
              />
              <Stack direction="row" spacing={1}>
                <Button
                  variant="contained"
                  color="success"
                  onClick={() => recordDecision(acId, tcId, "accept")}
                >
                  Accept
                </Button>
                <Button
                  variant="outlined"
                  color="warning"
                  disabled={draft.trim() === ""}
                  onClick={() =>
                    recordDecision(acId, tcId, "override", draft.trim())
                  }
                >
                  Override
                </Button>
              </Stack>
            </Box>
          )}
        </CardContent>
      </Card>
    );
  };

  const reviewedCount = Object.keys(decisions).length;
  const totalToReview = assessment
    ? assessment.missing_link_inferences.length +
      assessment.stale_link_detections.length
    : 0;

  return (
    <Container maxWidth="lg" sx={{ mt: 5, mb: 8 }}>
      <Typography variant="h3" align="center" gutterBottom>
        AI-Assisted Feature Readiness Assessment
      </Typography>

      {/* ---- Real statistics ---- */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ bgcolor: "#1976d2", color: "white" }}>
            <CardContent>
              <Typography variant="h6">Total features</Typography>
              <Typography variant="h3">{features.length}</Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ bgcolor: "#2e7d32", color: "white" }}>
            <CardContent>
              <Typography variant="h6">Ready</Typography>
              <Typography variant="h3">{readyCount}</Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ bgcolor: "#ed6c02", color: "white" }}>
            <CardContent>
              <Typography variant="h6">Not yet ready</Typography>
              <Typography variant="h3">{pendingCount}</Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ bgcolor: "#6a1b9a", color: "white" }}>
            <CardContent>
              <Typography variant="h6">Average score</Typography>
              <Typography variant="h3">{averageScore}%</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* ---- AI traceability assessment: the thesis contribution ---- */}
      <Card sx={{ mb: 4 }}>
        <CardContent>
          <Typography variant="h5" gutterBottom>
            Traceability review
          </Typography>
          <Typography color="text.secondary" sx={{ mb: 3 }}>
            The system has checked every requirement for two problems: a missing
            link to a test case, and a link that has gone out of date because the
            requirement changed. Accept each suggestion you agree with, or
            override it and say why.
          </Typography>

          {totalToReview > 0 && (
            <Typography variant="body2" sx={{ mb: 2 }}>
              Reviewed {reviewedCount} of {totalToReview}
            </Typography>
          )}

          {loadingAssessment && <LinearProgress sx={{ mb: 2 }} />}

          {assessment && (
            <>
              <Typography variant="h6" sx={{ mt: 2, mb: 1 }}>
                Requirements with no linked test case
              </Typography>
              {assessment.missing_link_inferences.length === 0 ? (
                <Typography color="text.secondary" sx={{ mb: 3 }}>
                  Every requirement has a linked test case.
                </Typography>
              ) : (
                assessment.missing_link_inferences.map((r) => (
                  <ReviewRow
                    key={r.ac_id}
                    acId={r.ac_id}
                    tcId={r.proposed_tc_id}
                    acText={r.ac_description}
                    tcText={r.proposed_tc_description}
                    status={r.status}
                    detail={r.detail}
                    score={r.similarity_score}
                  />
                ))
              )}

              <Divider sx={{ my: 3 }} />

              <Typography variant="h6" sx={{ mb: 1 }}>
                Links checked after a requirement changed
              </Typography>
              {assessment.stale_link_detections.length === 0 ? (
                <Typography color="text.secondary">
                  No requirements have changed since their tests were written.
                </Typography>
              ) : (
                assessment.stale_link_detections.map((r) => (
                  <ReviewRow
                    key={r.ac_id}
                    acId={r.ac_id}
                    tcId={r.tc_id}
                    acText={`Now reads: ${r.new_requirement_text}`}
                    tcText={`Previously read: ${r.old_requirement_text}`}
                    status={r.status}
                    detail={r.detail}
                    score={null}
                  />
                ))
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* ---- Per-feature readiness lookup ---- */}
      <Card sx={{ mb: 4 }}>
        <CardContent>
          <Typography variant="h5" gutterBottom>
            Check one feature
          </Typography>

          <FormControl fullWidth sx={{ mt: 1 }}>
            <InputLabel>Feature</InputLabel>
            <Select
              value={selectedFeature}
              label="Feature"
              onChange={(e) => setSelectedFeature(e.target.value)}
            >
              {features.map((feature) => (
                <MenuItem key={feature.feature_id} value={feature.feature_id}>
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
            Assess readiness
          </Button>
        </CardContent>
      </Card>

      {readiness && (
        <Card sx={{ mb: 4 }}>
          <CardContent>
            <Typography variant="h5" gutterBottom>
              {readiness.feature_name}
            </Typography>

            <Typography>
              <b>Feature ID:</b> {readiness.feature_id}
            </Typography>

            <Typography sx={{ mt: 2 }}>
              <b>Status:</b>{" "}
              <Chip
                label={readiness.status}
                color={chipColor(readiness.status)}
              />
            </Typography>

            <Typography sx={{ mt: 3 }}>Readiness score</Typography>

            <LinearProgress
              variant="determinate"
              value={readiness.readiness_score}
              sx={{ mt: 1, height: 12, borderRadius: 5 }}
            />

            <Typography sx={{ mt: 1 }}>
              {readiness.readiness_score}%
            </Typography>

            <Box sx={{ mt: 4 }}>
              <Typography variant="h6">What needs attention</Typography>

              {readiness.recommendations.length === 0 ? (
                <Typography color="green">
                  This feature is ready for production.
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

      {/* ---- Chart driven by real scores ---- */}
      <Card>
        <CardContent>
          <Typography variant="h5" gutterBottom>
            Readiness across all features
          </Typography>
          <ReadinessChart scores={allScores} />
        </CardContent>
      </Card>
    </Container>
  );
}

export default App;
