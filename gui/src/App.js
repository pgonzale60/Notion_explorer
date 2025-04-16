import React, { useEffect, useState } from "react";
import { 
  Container, Typography, List, ListItem, ListItemText, Box, Paper, Stack, Divider, Card, CardContent, Chip, 
  FormControl, InputLabel, Select, MenuItem, IconButton, Tooltip, Badge, Tab, Tabs,
  FormGroup, FormControlLabel, Switch, CircularProgress, OutlinedInput, Checkbox, ListItemIcon,
  Button, Dialog, DialogTitle, DialogContent, DialogActions
} from "@mui/material";
import SortIcon from "@mui/icons-material/Sort";
import FilterListIcon from "@mui/icons-material/FilterList";
import ArrowUpwardIcon from "@mui/icons-material/ArrowUpward";
import ArrowDownwardIcon from "@mui/icons-material/ArrowDownward";
import InfoIcon from "@mui/icons-material/Info";
import FilterAltIcon from '@mui/icons-material/FilterAlt';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';

function App() {
  // Data states
  const [notes, setNotes] = useState([]);
  const [answersIndex, setAnswersIndex] = useState({}); // noteId -> true if has answers
  const [noteVersionsIndex, setNoteVersionsIndex] = useState({}); // noteId -> [versions]
  const [selectedNote, setSelectedNote] = useState(null);
  const [answers, setAnswers] = useState([]);
  const [questionVersions, setQuestionVersions] = useState([]); // Available question versions from DB
  const [selectedVersions, setSelectedVersions] = useState([]); // Selected versions to display
  const [questions, setQuestions] = useState({}); // Format: { "v1": [question1, question2, ...], "v2": [...] }
  const [isLoadingQuestions, setIsLoadingQuestions] = useState(true);
  const [latestVersion, setLatestVersion] = useState(null); // Latest version
  
  // Filter states
  const [contentFilter, setContentFilter] = useState(false);
  const [analysisFilter, setAnalysisFilter] = useState(false);
  const [versionFilter, setVersionFilter] = useState("any");
  const [versionFilterSelections, setVersionFilterSelections] = useState([]); // For multiselect version filtering
  const [filterDialogOpen, setFilterDialogOpen] = useState(false);
  
  // Sort states
  const [sortDirection, setSortDirection] = useState("desc"); // "asc" or "desc"
  
  // Display states
  const [activeTab, setActiveTab] = useState(0); // 0: All, 1: Metadata, 2: Content, 3: Analysis
  const [viewMode, setViewMode] = useState("all"); // "all", "metadata", "content", "analysis"

  // Load data on component mount
  useEffect(() => {
    // Fetch notes
    fetch("http://localhost:8000/notes")
      .then((res) => res.json())
      .then(setNotes);
    
    // Fetch answer index
    fetch("http://localhost:8000/answers_index")
      .then((res) => res.json())
      .then((ids) => {
        const idx = {};
        ids.forEach((id) => idx[id] = true);
        setAnswersIndex(idx);
      });
    
    // Fetch note versions index (mapping of note_id -> list of versions)
    fetch("http://localhost:8000/note_versions_index")
      .then((res) => res.json())
      .then(setNoteVersionsIndex);
    
    // Fetch available question versions from the database
    fetchQuestionVersions();
  }, []);
  
  // Function to fetch all question versions and their questions
  const fetchQuestionVersions = async () => {
    setIsLoadingQuestions(true);
    
    try {
      // First, get all question versions from the database API
      const versionsResponse = await fetch("http://localhost:8000/question_versions");
      
      if (!versionsResponse.ok) {
        throw new Error("Failed to fetch question versions");
      }
      
      const versionData = await versionsResponse.json();
      
      // Extract version strings
      const versions = versionData.map(v => v.version);
      setQuestionVersions(versions);
      
      // Get the latest version
      const latestResponse = await fetch("http://localhost:8000/latest_question_version");
      if (latestResponse.ok) {
        const latestData = await latestResponse.json();
        const latest = latestData.version;
        setLatestVersion(latest);
        // Set the latest version as the default selected version
        setSelectedVersions(latest ? [latest] : []);
      }
      
      // Load questions for each version
      const questionsMap = {};
      
      for (const version of versions) {
        try {
          const questionsResponse = await fetch(`http://localhost:8000/questions/${version}`);
          
          if (questionsResponse.ok) {
            const data = await questionsResponse.json();
            
            // Store the questions array for this version
            questionsMap[version] = data.questions || [];
          }
        } catch (error) {
          console.error(`Error loading questions for ${version}:`, error);
        }
      }
      
      setQuestions(questionsMap);
    } catch (error) {
      console.error("Error fetching question versions:", error);
      
      // Fallback: Use hardcoded question versions if API fails
      const fallbackVersions = ["v1", "v2", "v3", "v4"];
      setQuestionVersions(fallbackVersions);
      setLatestVersion("v4");
      setSelectedVersions(["v4"]);
      
      // Attempt to fetch individual question files directly as a fallback
      const questionsMap = {};
      
      for (const version of fallbackVersions) {
        try {
          const response = await fetch(`http://localhost:8000/questions/${version}`);
          
          if (response.ok) {
            const data = await response.json();
            questionsMap[version] = data.questions || [];
          }
        } catch (err) {
          console.error(`Failed to fetch ${version} questions:`, err);
        }
      }
      
      // If we still don't have questions, use hardcoded fallbacks
      if (Object.keys(questionsMap).length === 0) {
        setQuestions({
          "v1": [
            "What positive emotions were mentioned?",
            "What negative emotions were mentioned?",
            "What behaviors do I admire?",
            "What topics am I interested in?",
            "What activities do I engage in?",
            "What problems am I trying to solve?",
            "What criteria did I use for decision making?",
            "Do I regret any decisions?",
            "What trade-offs did I consider?",
            "How do I describe myself?",
            "What aspects of myself do I want to change?",
            "What roles do I adopt?"
          ],
          "v2": [
            "What experiences triggered positive emotional responses?",
            "What situations caused me to feel aligned with my actions?",
            "What situations caused me to feel misaligned with my actions?",
            "What behaviours or qualities do I admire in others?",
            "What behaviours or qualities do I criticise in others?",
            "What topics and activities am I interested in?",
            "What problems am I trying to solve?"
          ],
          "v3": [
            "What experiences triggered positive emotional responses?",
            "What situations caused me to feel aligned with my actions?",
            "What situations caused me to feel misaligned with my actions?",
            "What behaviours or qualities do I admire in others?",
            "What behaviours or qualities do I criticise in others?",
            "What topics and activities am I interested in?",
            "Where do I invest my energy when nobody is directing me?",
            "What problems am I trying to solve?",
            "What criteria did I use to make choices?",
            "Was I satisfied with any decisions?",
            "Was I regretting any decisions?",
            "What trade-offs did I consider when making a decision?",
            "How do I describe myself in contrast to others?",
            "What aspects of myself do I question or want to change?",
            "What roles do I adopt?",
            "What is the main theme or focus of the note?"
          ]
        });
      } else {
        setQuestions(questionsMap);
      }
    } finally {
      setIsLoadingQuestions(false);
    }
  };

  // Handle version selection
  const handleVersionChange = (event) => {
    const { value } = event.target;
    setSelectedVersions(Array.isArray(value) ? value : [value]);
  };
  
  // Handle version filter change
  const handleVersionFilterChange = (event) => {
    setVersionFilter(event.target.value);
  };

  // Handle open/close filter dialog
  const openFilterDialog = () => {
    setFilterDialogOpen(true);
  };

  const closeFilterDialog = () => {
    setFilterDialogOpen(false);
  };

  // Handle version filter selection in dialog
  const handleFilterVersionSelectionChange = (event) => {
    setVersionFilterSelections(event.target.value);
  };

  const applyVersionFilter = () => {
    closeFilterDialog();
  };
  
  const selectNote = (note) => {
    setSelectedNote(note);
    fetch(`http://localhost:8000/answers/${note.id}`)
      .then((res) => res.json())
      .then(setAnswers);
  };

  // Handle sort direction change
  const toggleSortDirection = () => {
    setSortDirection(sortDirection === "asc" ? "desc" : "asc");
  };
  
  // Handle tab change
  const handleTabChange = (event, newValue) => {
    setActiveTab(newValue);
    // Map tab index to view mode
    const modes = ["all", "metadata", "content", "analysis"];
    setViewMode(modes[newValue]);
  };

  // Filter and sort notes
  const processedNotes = React.useMemo(() => {
    // Step 1: Filter notes
    let filtered = [...notes];
    
    // Apply content filter
    if (contentFilter) {
      filtered = filtered.filter((note) => note.content && note.content.trim().length > 0);
    }
    
    // Apply analysis filter
    if (analysisFilter) {
      filtered = filtered.filter((note) => answersIndex[note.id]);
    }

    // Apply version filter if specific version is selected
    if (versionFilter !== "any") {
      filtered = filtered.filter((note) => {
        // Check if this note has answers for the selected version
        return noteVersionsIndex[note.id]?.includes(versionFilter);
      });
    }
    // Apply version filter selections (from the filter dialog)
    else if (versionFilterSelections.length > 0) {
      filtered = filtered.filter((note) => {
        // Check if this note has answers for any of the selected versions
        return versionFilterSelections.some(version => 
          noteVersionsIndex[note.id]?.includes(version)
        );
      });
    }
    
    // Step 2: Sort notes (by last_edited_time)
    filtered.sort((a, b) => {
      const timeA = new Date(a.last_edited_time || 0).getTime();
      const timeB = new Date(b.last_edited_time || 0).getTime();
      
      return sortDirection === "asc" ? timeA - timeB : timeB - timeA;
    });
    
    return filtered;
  }, [notes, contentFilter, analysisFilter, sortDirection, answersIndex, versionFilterSelections, versionFilter, noteVersionsIndex]);

  // Get formatted date for display
  const getFormattedDate = (dateString) => {
    if (!dateString) return "Unknown date";
    const date = new Date(dateString);
    return date.toLocaleDateString("en-GB", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  // Get question text for a specific version and question number
  const getQuestionText = (version, questionNumber) => {
    // Convert from 1-based to 0-based index
    const idx = parseInt(questionNumber.replace("q", "")) - 1;
    
    if (questions[version] && questions[version][idx]) {
      return questions[version][idx];
    }
    
    return "Question not found";
  };

  // Get unique answer versions for the current note
  const answerVersions = Array.from(new Set(answers.map((a) => a.questions_version))).sort((a, b) => {
    // Sort versions in descending order (newest to oldest)
    // Assuming format vX where X is a number
    const numA = parseInt(a.replace("v", ""));
    const numB = parseInt(b.replace("v", ""));
    return numB - numA;
  });

  // Determine if answers for a specific version exist
  const hasAnswersForVersion = (version) => {
    return answers.some((a) => a.questions_version === version);
  };

  // Get versions to display based on current selection
  const versionsToDisplay = React.useMemo(() => {
    if (versionFilter === "any") {
      // When "Any version" is selected, check if there are version filter selections
      if (versionFilterSelections.length > 0) {
        // Only show selected versions from the filter dialog
        return answerVersions.filter(v => versionFilterSelections.includes(v));
      }
      // Otherwise show all versions from newest to oldest
      return answerVersions;
    } else {
      // When a specific version is selected in the dropdown
      return [versionFilter];
    }
  }, [versionFilter, versionFilterSelections, answerVersions]);

  // Sort questionVersions from newest to oldest for display in the filter dialog
  const sortedQuestionVersions = React.useMemo(() => {
    return [...questionVersions].sort((a, b) => {
      const numA = parseInt(a.replace("v", ""));
      const numB = parseInt(b.replace("v", ""));
      return numB - numA;
    });
  }, [questionVersions]);

  return (
    <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
      <Typography variant="h4" gutterBottom>
        Notion Theme Explorer
      </Typography>

      {/* Filters and Controls */}
      <Paper 
        elevation={1} 
        sx={{ 
          p: 2, 
          mb: 2, 
          display: 'flex', 
          flexDirection: { xs: 'column', sm: 'row' }, 
          justifyContent: 'space-between',
          alignItems: { xs: 'flex-start', sm: 'center' },
          gap: 2
        }}
      >
        {/* Sort Control */}
        <Stack direction="row" alignItems="center" spacing={1}>
          <Typography variant="subtitle2" component="span">
            <Box component="span" sx={{ display: 'flex', alignItems: 'center' }}>
              <SortIcon fontSize="small" sx={{ mr: 0.5 }} /> Sort:
            </Box>
          </Typography>
          <IconButton 
            size="small" 
            onClick={toggleSortDirection}
            sx={{ 
              border: '1px solid rgba(0, 0, 0, 0.23)', 
              borderRadius: 1,
              p: 1
            }}
          >
            {sortDirection === "asc" ? <ArrowUpwardIcon /> : <ArrowDownwardIcon />}
          </IconButton>
        </Stack>

        {/* Filters */}
        <Stack direction="row" alignItems="center" spacing={2}>
          <Typography variant="subtitle2" component="span">
            <Box component="span" sx={{ display: 'flex', alignItems: 'center' }}>
              <FilterListIcon fontSize="small" sx={{ mr: 0.5 }} /> Filters:
            </Box>
          </Typography>

          <FormGroup row>
            <FormControlLabel
              control={
                <Switch
                  size="small"
                  checked={contentFilter}
                  onChange={(e) => setContentFilter(e.target.checked)}
                />
              }
              label="Has Content"
            />

            <FormControlLabel
              control={
                <Switch
                  size="small"
                  checked={analysisFilter}
                  onChange={(e) => setAnalysisFilter(e.target.checked)}
                />
              }
              label="Has Analysis"
            />
          </FormGroup>

          {/* Version Filter Dropdown */}
          <FormControl sx={{ minWidth: 120 }} size="small">
            <InputLabel id="question-version-label">Question Version</InputLabel>
            <Select
              labelId="question-version-label"
              id="question-version-select"
              value={versionFilter}
              label="Question Version"
              onChange={handleVersionFilterChange}
            >
              <MenuItem value="any">Any Version</MenuItem>
              {sortedQuestionVersions.map((version) => (
                <MenuItem key={`version-${version}`} value={version}>
                  {version}
                  {version === latestVersion && " (Latest)"}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          {/* Version Filter Button */}
          <Tooltip title="Filter notes by version">
            <IconButton onClick={openFilterDialog} sx={{ ml: 1 }}>
              <FilterAltIcon />
              {versionFilterSelections.length > 0 && (
                <Badge 
                  color="primary" 
                  badgeContent={versionFilterSelections.length} 
                  sx={{ position: 'absolute', top: -5, right: -5 }}
                />
              )}
            </IconButton>
          </Tooltip>
        </Stack>
      </Paper>

      {/* Version Filter Dialog */}
      <Dialog open={filterDialogOpen} onClose={closeFilterDialog}>
        <DialogTitle>Filter Notes by Question Version</DialogTitle>
        <DialogContent>
          <FormControl sx={{ mt: 2, width: '100%', minWidth: 200 }}>
            <InputLabel id="version-filter-select-label">Filter Versions</InputLabel>
            <Select
              labelId="version-filter-select-label"
              id="version-filter-select"
              multiple
              value={versionFilterSelections}
              onChange={handleFilterVersionSelectionChange}
              input={<OutlinedInput label="Filter Versions" />}
              renderValue={(selected) => (
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                  {selected.map((value) => (
                    <Chip key={value} label={value} />
                  ))}
                </Box>
              )}
            >
              {sortedQuestionVersions.map((version) => (
                <MenuItem key={`filter-${version}`} value={version}>
                  <Checkbox checked={versionFilterSelections.indexOf(version) > -1} />
                  <ListItemText 
                    primary={version} 
                    secondary={version === latestVersion ? "Latest" : ""}
                  />
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <Typography variant="caption" sx={{ display: 'block', mt: 1 }}>
            Only show notes that have answers for the selected versions
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={closeFilterDialog}>Cancel</Button>
          <Button onClick={applyVersionFilter} variant="contained" color="primary">
            Apply Filter
          </Button>
        </DialogActions>
      </Dialog>

      <Box sx={{ display: 'flex', flexDirection: { xs: 'column', md: 'row' }, gap: 2 }}>
        {/* Left Panel: Note List */}
        <Paper sx={{ width: { xs: '100%', md: '30%' }, height: 'calc(100vh - 200px)', overflow: 'auto' }}>
          <Box sx={{ p: 2, borderBottom: '1px solid rgba(0, 0, 0, 0.12)' }}>
            <Typography variant="h6">
              Notes
              <Typography variant="caption" sx={{ ml: 1 }}>
                Showing: {processedNotes.length}
              </Typography>
            </Typography>
          </Box>
          
          <List sx={{ p: 0 }}>
            {processedNotes.map((note) => (
              <ListItem
                key={note.id}
                alignItems="flex-start"
                sx={{
                  cursor: 'pointer',
                  borderLeft: selectedNote?.id === note.id ? '4px solid #1976d2' : '4px solid transparent',
                  backgroundColor: selectedNote?.id === note.id ? 'rgba(25, 118, 210, 0.08)' : 'transparent',
                  '&:hover': {
                    backgroundColor: 'rgba(0, 0, 0, 0.04)',
                  },
                  transition: 'all 0.2s',
                }}
                onClick={() => selectNote(note)}
              >
                <ListItemText
                  primary={
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Typography variant="subtitle1" 
                        sx={{ 
                          fontWeight: selectedNote?.id === note.id ? 'bold' : 'normal',
                          maxWidth: '70%',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {/* Extract title from first line of content or use ID */}
                        {note.content 
                          ? note.content.split('\n')[0].substr(0, 40) 
                          : note.id.substr(0, 10) + '...'}
                      </Typography>
                      
                      {answersIndex[note.id] && (
                        <Chip 
                          label="Analyzed" 
                          size="small" 
                          color="primary" 
                          variant="outlined" 
                          sx={{ fontSize: '0.7rem' }}
                        />
                      )}
                    </Box>
                  }
                  secondary={
                    <Typography
                      variant="body2"
                      color="text.secondary"
                    >
                      {getFormattedDate(note.last_edited_time)}
                    </Typography>
                  }
                />
              </ListItem>
            ))}
          </List>
        </Paper>

        {/* Right Panel: Details */}
        <Box sx={{ width: { xs: '100%', md: '70%' } }}>
          {selectedNote ? (
            <>
              {/* Tabs for switching views */}
              <Tabs value={activeTab} onChange={handleTabChange} sx={{ mb: 2 }}>
                <Tab label="All" />
                <Tab label="Metadata" />
                <Tab label="Content" />
                <Tab label="Analysis" />
              </Tabs>
              
              {/* Note Content */}
              {(viewMode === "all" || viewMode === "content") && (
                <Paper elevation={1} sx={{ p: 2, mb: 3 }}>
                  <Box sx={{ 
                    whiteSpace: 'pre-wrap', 
                    fontFamily: 'monospace',
                    maxHeight: '300px',
                    overflow: 'auto'
                  }}>
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      rehypePlugins={[rehypeHighlight]}
                    >
                      {selectedNote.content || "*No content available*"}
                    </ReactMarkdown>
                  </Box>
                </Paper>
              )}
              
              {/* Gemini Analysis */}
              {(viewMode === "all" || viewMode === "analysis") && (
                <Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                    <Typography variant="h6">
                      Gemini Analysis
                    </Typography>
                    <Chip label={`${answers.length} Results`} color="primary" />
                  </Box>
                  
                  {isLoadingQuestions ? (
                    <CircularProgress />
                  ) : versionsToDisplay.length === 0 ? (
                    <Typography color="text.secondary">No analysis available for this note.</Typography>
                  ) : (
                    // Map through versions to display
                    versionsToDisplay.map((version) => {
                      const answer = answers.find(a => a.questions_version === version);
                      if (!answer) return null;
                      
                      return (
                        <Box key={version} sx={{ mb: 4 }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                            <Chip 
                              label={`Version ${version}`} 
                              size="small" 
                              sx={{ mr: 1 }} 
                            />
                            <Chip 
                              label={answer.model} 
                              size="small" 
                              variant="outlined"
                            />
                            {version === latestVersion && (
                              <Chip size="small" color="primary" label="Latest" sx={{ ml: 1 }} />
                            )}
                            <Typography variant="caption" sx={{ ml: 'auto' }}>
                              {getFormattedDate(answer.date_executed)}
                            </Typography>
                          </Box>
                          
                          {/* Questions and Answers */}
                          <List sx={{ mt: 1 }}>
                            {Object.entries(answer.answers_json).map(([qNum, answerText]) => (
                              <Card key={`${version}-${qNum}`} variant="outlined" sx={{ mb: 2 }}>
                                <CardContent>
                                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                                    <Tooltip title={getQuestionText(version, qNum)}>
                                      <Typography variant="subtitle1" color="text.secondary" sx={{ display: 'flex', alignItems: 'center' }}>
                                        {qNum.toUpperCase()} <InfoIcon fontSize="small" sx={{ ml: 0.5 }} />
                                      </Typography>
                                    </Tooltip>
                                  </Box>
                                  <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
                                    <ReactMarkdown
                                      remarkPlugins={[remarkGfm]}
                                      rehypePlugins={[rehypeHighlight]}
                                    >
                                      {answerText}
                                    </ReactMarkdown>
                                  </Typography>
                                </CardContent>
                              </Card>
                            ))}
                          </List>
                        </Box>
                      );
                    })
                  )}
                </Box>
              )}
              
              {/* Metadata Section */}
              {(viewMode === "all" || viewMode === "metadata") && (
                <Paper elevation={1} sx={{ mt: 3, p: 2 }}>
                  <Typography variant="h6" gutterBottom>
                    Metadata
                  </Typography>
                  <Stack spacing={1}>
                    <Box>
                      <Typography variant="caption" color="text.secondary">ID</Typography>
                      <Typography variant="body2">{selectedNote.id}</Typography>
                    </Box>
                    {selectedNote.parent_id && (
                      <Box>
                        <Typography variant="caption" color="text.secondary">Parent ID</Typography>
                        <Typography variant="body2">{selectedNote.parent_id}</Typography>
                      </Box>
                    )}
                    {selectedNote.created_time && (
                      <Box>
                        <Typography variant="caption" color="text.secondary">Created</Typography>
                        <Typography variant="body2">{getFormattedDate(selectedNote.created_time)}</Typography>
                      </Box>
                    )}
                    {selectedNote.last_edited_time && (
                      <Box>
                        <Typography variant="caption" color="text.secondary">Last Edited</Typography>
                        <Typography variant="body2">{getFormattedDate(selectedNote.last_edited_time)}</Typography>
                      </Box>
                    )}
                  </Stack>
                </Paper>
              )}
            </>
          ) : (
            <Paper 
              elevation={1} 
              sx={{ 
                p: 4, 
                height: '300px', 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center',
                flexDirection: 'column',
                gap: 2
              }}
            >
              <Typography variant="h6" color="text.secondary">
                Select a note to view details
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {processedNotes.length === 0 ? (
                  "No notes found. Try changing your filters."
                ) : (
                  `${processedNotes.length} notes available`
                )}
              </Typography>
            </Paper>
          )}
        </Box>
      </Box>
    </Container>
  );
}

export default App;
