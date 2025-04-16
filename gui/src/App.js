import React, { useEffect, useState } from "react";
import { 
  Container, Typography, List, ListItem, ListItemText, Box, Paper, Stack, Divider, Card, CardContent, Chip, 
  FormControl, InputLabel, Select, MenuItem, IconButton, Tooltip, Badge, Tab, Tabs,
  FormGroup, FormControlLabel, Switch, CircularProgress
} from "@mui/material";
import SortIcon from "@mui/icons-material/Sort";
import FilterListIcon from "@mui/icons-material/FilterList";
import ArrowUpwardIcon from "@mui/icons-material/ArrowUpward";
import ArrowDownwardIcon from "@mui/icons-material/ArrowDownward";
import InfoIcon from "@mui/icons-material/Info";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';

function App() {
  // Data states
  const [notes, setNotes] = useState([]);
  const [answersIndex, setAnswersIndex] = useState({}); // noteId -> true if has answers
  const [selectedNote, setSelectedNote] = useState(null);
  const [answers, setAnswers] = useState([]);
  const [questionVersions, setQuestionVersions] = useState(["v1", "v2", "v3"]); // Initialize with default values
  const [questions, setQuestions] = useState({}); // Format: { "v1": [question1, question2, ...], "v2": [...] }
  const [isLoadingQuestions, setIsLoadingQuestions] = useState(true);
  
  // Filter states
  const [contentFilter, setContentFilter] = useState(false);
  const [analysisFilter, setAnalysisFilter] = useState(false);
  const [versionFilter, setVersionFilter] = useState("any");
  
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
    
    // Fetch available question versions from the questions directory
    fetchQuestionVersions();
  }, []);
  
  // Function to fetch all question versions and their questions
  const fetchQuestionVersions = async () => {
    setIsLoadingQuestions(true);
    
    try {
      // First, get all question version files
      const response = await fetch("http://localhost:8000/question_files");
      
      if (!response.ok) {
        throw new Error("Failed to fetch question files");
      }
      
      const files = await response.json();
      
      // Extract version numbers from filenames (e.g., "questions_v1.json" -> "v1")
      const versions = files
        .filter(file => file.match(/questions_v\d+\.json/))
        .map(file => {
          const match = file.match(/questions_v(\d+)\.json/);
          return match ? `v${match[1]}` : null;
        })
        .filter(Boolean);
        
      setQuestionVersions(versions);
      
      // Next, load questions for each version
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
      const fallbackVersions = ["v1", "v2", "v3"];
      setQuestionVersions(fallbackVersions);
      
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
    
    // Content filter
    if (contentFilter) {
      filtered = filtered.filter(note => 
        note.content && note.content.trim() !== ""
      );
    }
    
    // Analysis filter
    if (analysisFilter) {
      filtered = filtered.filter(note => answersIndex[note.id]);
    }
    
    // Version filter (would need to enhance the backend API)
    if (versionFilter !== "any") {
      // This is a placeholder - the actual implementation would require
      // a backend endpoint that provides version info per note
      // For now, we just keep the UI ready
    }
    
    // Step 2: Sort notes by last_edited_time
    return filtered.sort((a, b) => {
      // Handle missing dates
      if (!a.last_edited_time) return sortDirection === "asc" ? -1 : 1;
      if (!b.last_edited_time) return sortDirection === "asc" ? 1 : -1;
      
      // Compare dates
      const dateA = new Date(a.last_edited_time);
      const dateB = new Date(b.last_edited_time);
      
      if (sortDirection === "asc") {
        return dateA - dateB;
      } else {
        return dateB - dateA;
      }
    });
  }, [notes, contentFilter, analysisFilter, versionFilter, sortDirection, answersIndex]);

  // Extract title from note content (first line without the # prefix)
  const getNoteTitle = (content) => {
    if (!content) return "Untitled";
    const firstLine = content.split('\n')[0];
    return firstLine.replace(/^#+\s*/, '').trim() || "Untitled";
  };

  // Format date for display
  const formatDate = (dateString) => {
    if (!dateString) return "N/A";
    const date = new Date(dateString);
    return date.toLocaleString(undefined, { 
      year: 'numeric', 
      month: 'short', 
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };
  
  // Get question text for an answer key (e.g., "q1" -> "What positive emotions were mentioned?")
  const getQuestionForKey = (key, version) => {
    if (!version) return "Unknown question";
    
    // Remove 'v' prefix if present to normalize version format
    const versionKey = version.replace(/^v/, '');
    
    // Extract the number from the key (e.g., "q1" -> 1)
    const match = key.match(/q(\d+)/);
    if (!match) return "Unknown question";
    
    const questionIndex = parseInt(match[1], 10) - 1;
    
    // Get questions for this version
    const versionQuestions = questions[`v${versionKey}`] || [];
    
    // Return the question if it exists, otherwise a fallback message
    if (questionIndex >= 0 && questionIndex < versionQuestions.length) {
      return versionQuestions[questionIndex];
    }
    
    return "Question not found";
  };

  return (
    <Container maxWidth="lg" sx={{ paddingTop: 3, paddingBottom: 3 }}>
      <Typography variant="h4" gutterBottom sx={{ fontWeight: 'medium' }}>Notion Notes Explorer</Typography>
      
      {/* Filters and Controls */}
      <Paper 
        elevation={1} 
        sx={{ 
          p: 2, 
          mb: 3, 
          borderRadius: 2,
          backgroundColor: '#f8f9fa'
        }}
      >
        <Stack 
          direction={{ xs: 'column', sm: 'row' }} 
          spacing={3} 
          alignItems={{ xs: 'flex-start', sm: 'center' }}
          justifyContent="space-between"
          flexWrap="wrap"
        >
          {/* Left section - Sort controls */}
          <Stack direction="row" spacing={2} alignItems="center">
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <Typography variant="subtitle2" sx={{ mr: 1 }}>
                <SortIcon fontSize="small" sx={{ verticalAlign: 'middle', mr: 0.5 }} />
                Sort:
              </Typography>
              <Tooltip title={sortDirection === "asc" ? "Oldest first" : "Newest first"}>
                <IconButton 
                  onClick={toggleSortDirection} 
                  size="small" 
                  color="primary"
                  sx={{ border: '1px solid', borderColor: 'primary.main', borderRadius: 1 }}
                >
                  {sortDirection === "asc" ? <ArrowUpwardIcon fontSize="small" /> : <ArrowDownwardIcon fontSize="small" />}
                </IconButton>
              </Tooltip>
            </Box>
          </Stack>
          
          {/* Right section - Filter controls */}
          <Stack direction="row" spacing={2} alignItems="center" flexWrap="wrap">
            <Typography variant="subtitle2">
              <FilterListIcon fontSize="small" sx={{ verticalAlign: 'middle', mr: 0.5 }} />
              Filters:
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
                label={<Typography variant="body2">Has Content</Typography>}
              />
              
              <FormControlLabel 
                control={
                  <Switch 
                    size="small" 
                    checked={analysisFilter}
                    onChange={(e) => setAnalysisFilter(e.target.checked)}
                  />
                } 
                label={<Typography variant="body2">Has Analysis</Typography>}
              />
            </FormGroup>
            
            <FormControl variant="outlined" size="small" sx={{ minWidth: 150 }}>
              <InputLabel id="version-filter-label">Question Version</InputLabel>
              <Select
                labelId="version-filter-label"
                value={versionFilter}
                label="Question Version"
                onChange={(e) => setVersionFilter(e.target.value)}
                sx={{ height: 40 }}
                disabled={isLoadingQuestions}
              >
                <MenuItem value="any">Any Version</MenuItem>
                {Array.isArray(questionVersions) && questionVersions.map(version => (
                  <MenuItem key={version} value={version}>{version}</MenuItem>
                ))}
              </Select>
              {isLoadingQuestions && (
                <CircularProgress 
                  size={16} 
                  sx={{ ml: 1, position: 'absolute', right: 32, top: '50%', transform: 'translateY(-50%)' }}
                />
              )}
            </FormControl>
          </Stack>
        </Stack>
      </Paper>
      
      {/* Main content area */}
      <Box sx={{ display: "flex", gap: 3 }}>
        {/* Note list panel */}
        <Paper sx={{ 
          flex: 1, 
          maxWidth: 350,
          maxHeight: 'calc(100vh - 220px)', 
          overflow: "auto", 
          boxShadow: 2,
          borderRadius: 2
        }}>
          <Box sx={{ 
            p: 2, 
            backgroundColor: '#f5f5f5', 
            borderBottom: '1px solid #e0e0e0',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}>
            <Typography variant="h6">Notes</Typography>
            <Badge 
              badgeContent={processedNotes.length} 
              color="primary"
              sx={{ '& .MuiBadge-badge': { fontSize: '0.8rem' } }}
            >
              <Typography variant="body2" color="text.secondary">Showing</Typography>
            </Badge>
          </Box>
          
          {processedNotes.length === 0 ? (
            <Box sx={{ p: 3, textAlign: 'center' }}>
              <Typography color="text.secondary">No notes match your filters</Typography>
            </Box>
          ) : (
            <List sx={{ p: 0 }}>
              {processedNotes.map((note) => (
                <React.Fragment key={note.id}>
                  <ListItem 
                    button 
                    onClick={() => selectNote(note)} 
                    selected={selectedNote && selectedNote.id === note.id}
                    sx={{ 
                      px: 2, 
                      py: 1.5,
                      '&.Mui-selected': {
                        backgroundColor: '#e3f2fd'
                      },
                      '&:hover': {
                        backgroundColor: '#f5f5f5'
                      }
                    }}
                  >
                    <ListItemText
                      primary={getNoteTitle(note.content)}
                      secondary={
                        <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', fontSize: '0.7rem' }}>
                          {formatDate(note.last_edited_time)}
                        </Typography>
                      }
                      primaryTypographyProps={{
                        noWrap: true,
                        style: { fontWeight: 500 }
                      }}
                    />
                    {answersIndex[note.id] && (
                      <Chip 
                        size="small" 
                        label="Analyzed" 
                        sx={{ ml: 1, fontSize: '0.7rem', height: 20 }} 
                        color="primary" 
                        variant="outlined" 
                      />
                    )}
                  </ListItem>
                  <Divider component="li" />
                </React.Fragment>
              ))}
            </List>
          )}
        </Paper>
        
        {/* Note detail panel */}
        <Paper sx={{ 
          flex: 2, 
          p: 0, 
          maxHeight: 'calc(100vh - 220px)', 
          overflow: "auto",
          boxShadow: 2,
          borderRadius: 2
        }}>
          {selectedNote ? (
            <>
              {/* Header with title and metadata */}
              <Box sx={{ p: 3, borderBottom: '1px solid #e0e0e0', backgroundColor: '#f9f9f9' }}>
                <Typography variant="h6">{getNoteTitle(selectedNote.content)}</Typography>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 1 }}>
                  <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                    ID: {selectedNote.id}
                  </Typography>
                  <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                    Created: {formatDate(selectedNote.created_time)} | Last Edited: {formatDate(selectedNote.last_edited_time)}
                  </Typography>
                </Box>
              </Box>
              
              {/* Tabs for content navigation */}
              <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
                <Tabs 
                  value={activeTab} 
                  onChange={handleTabChange} 
                  variant="fullWidth"
                  indicatorColor="primary"
                  textColor="primary"
                >
                  <Tab label="All" />
                  <Tab label="Metadata" />
                  <Tab label="Content" />
                  <Tab label="Analysis" />
                </Tabs>
              </Box>
              
              {/* Content sections based on active tab */}
              <Box sx={{ p: 3 }}>
                {/* Metadata Section */}
                {(viewMode === 'all' || viewMode === 'metadata') && (
                  <Box sx={{ mb: viewMode === 'all' ? 3 : 0 }}>
                    {viewMode === 'all' && <Typography variant="h6" gutterBottom>Metadata</Typography>}
                    <Card variant="outlined" sx={{ mb: 2 }}>
                      <CardContent>
                        <Typography variant="body2" component="div">
                          <Box component="span" sx={{ fontWeight: 'bold', color: 'text.secondary', display: 'inline-block', width: 120 }}>
                            ID:
                          </Box>
                          {selectedNote.id}
                        </Typography>
                        <Typography variant="body2" component="div">
                          <Box component="span" sx={{ fontWeight: 'bold', color: 'text.secondary', display: 'inline-block', width: 120 }}>
                            Created:
                          </Box>
                          {formatDate(selectedNote.created_time)}
                        </Typography>
                        <Typography variant="body2" component="div">
                          <Box component="span" sx={{ fontWeight: 'bold', color: 'text.secondary', display: 'inline-block', width: 120 }}>
                            Last Edited:
                          </Box>
                          {formatDate(selectedNote.last_edited_time)}
                        </Typography>
                        {selectedNote.parent_id && (
                          <Typography variant="body2" component="div">
                            <Box component="span" sx={{ fontWeight: 'bold', color: 'text.secondary', display: 'inline-block', width: 120 }}>
                              Parent ID:
                            </Box>
                            {selectedNote.parent_id}
                          </Typography>
                        )}
                      </CardContent>
                    </Card>
                  </Box>
                )}

                {/* Content Section - Markdown Rendering */}
                {(viewMode === 'all' || viewMode === 'content') && selectedNote.content && (
                  <Box sx={{ mb: viewMode === 'all' ? 3 : 0 }}>
                    {viewMode === 'all' && (
                      <Typography variant="h6" gutterBottom>Content</Typography>
                    )}
                    <Card variant="outlined" sx={{ mb: 2 }}>
                      <CardContent sx={{ 
                        '& code': { 
                          backgroundColor: '#f5f5f5', 
                          padding: '2px 4px', 
                          borderRadius: 1,
                          fontFamily: 'monospace' 
                        },
                        '& pre': {
                          backgroundColor: '#f5f5f5',
                          padding: 2,
                          borderRadius: 1,
                          overflow: 'auto'
                        },
                        '& h1, & h2, & h3, & h4, & h5, & h6': {
                          marginTop: 2,
                          marginBottom: 1,
                          fontWeight: 'bold'
                        },
                        '& p': {
                          marginBottom: 1.5
                        }
                      }}>
                        <ReactMarkdown 
                          remarkPlugins={[remarkGfm]} 
                          rehypePlugins={[rehypeHighlight]}
                        >
                          {selectedNote.content}
                        </ReactMarkdown>
                      </CardContent>
                    </Card>
                  </Box>
                )}

                {/* Analysis Section */}
                {(viewMode === 'all' || viewMode === 'analysis') && (
                  <Box>
                    {viewMode === 'all' && (
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                        <Typography variant="h6">Gemini Analysis</Typography>
                        {answers.length > 0 && (
                          <Chip 
                            size="small" 
                            label={`${answers.length} ${answers.length === 1 ? 'Result' : 'Results'}`} 
                            color="primary" 
                          />
                        )}
                      </Box>
                    )}
                    
                    {isLoadingQuestions ? (
                      <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
                        <CircularProgress size={24} />
                        <Typography variant="body2" sx={{ ml: 2 }}>Loading questions...</Typography>
                      </Box>
                    ) : answers.length === 0 ? (
                      <Typography>No analysis found for this note.</Typography>
                    ) : (
                      answers.map((ans, idx) => (
                        <Card key={idx} variant="outlined" sx={{ mb: 3, backgroundColor: '#fafafa' }}>
                          <CardContent>
                            {/* Analysis header with metadata */}
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                              <Stack direction="row" spacing={1} flexWrap="wrap">
                                <Chip 
                                  size="small" 
                                  label={`Version ${ans.questions_version}`} 
                                  color="primary"
                                  variant="outlined"
                                />
                                <Chip 
                                  size="small" 
                                  label={ans.model} 
                                  color="secondary"
                                  variant="outlined"
                                />
                              </Stack>
                              {ans.date_executed && (
                                <Typography variant="caption" color="text.secondary">
                                  {formatDate(ans.date_executed)}
                                </Typography>
                              )}
                            </Box>
                            
                            {/* Answers display */}
                            <Box sx={{ 
                              backgroundColor: '#f5f5f5',
                              borderRadius: 1,
                              overflow: 'hidden'
                            }}>
                              {ans.answers_json && Object.entries(ans.answers_json).map(([key, value], i) => {
                                const question = getQuestionForKey(key, ans.questions_version);
                                return (
                                  <Box 
                                    key={key}
                                    sx={{ 
                                      p: 2, 
                                      borderBottom: i < Object.keys(ans.answers_json).length - 1 ? '1px solid #e0e0e0' : 'none',
                                      '&:hover': {
                                        backgroundColor: '#eef5fd'
                                      }
                                    }}
                                  >
                                    <Box sx={{ display: 'flex', alignItems: 'flex-start', mb: 1 }}>
                                      <Tooltip title={question} placement="top-start">
                                        <Box sx={{ 
                                          display: 'flex', 
                                          alignItems: 'center', 
                                          cursor: 'help',
                                          color: 'primary.main',
                                          fontWeight: 'medium',
                                          mr: 1,
                                          '&:hover': { textDecoration: 'underline' }
                                        }}>
                                          <Typography variant="subtitle2" component="span">
                                            {key.toUpperCase()}
                                          </Typography>
                                          <InfoIcon fontSize="small" sx={{ ml: 0.5, fontSize: '1rem' }} />
                                        </Box>
                                      </Tooltip>
                                      <Typography 
                                        variant="body2" 
                                        sx={{ 
                                          flex: 1,
                                          fontStyle: value === "Not mentioned." ? 'italic' : 'normal',
                                          color: value === "Not mentioned." ? 'text.secondary' : 'text.primary'
                                        }}
                                      >
                                        {value}
                                      </Typography>
                                    </Box>
                                  </Box>
                                );
                              })}
                            </Box>
                          </CardContent>
                        </Card>
                      ))
                    )}
                  </Box>
                )}
              </Box>
            </>
          ) : (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', p: 4 }}>
              <Typography sx={{ color: 'text.secondary' }}>Select a note to view details.</Typography>
            </Box>
          )}
        </Paper>
      </Box>
    </Container>
  );
}

export default App;
