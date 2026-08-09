import { 
  Container, 
  Box, 
  Typography, 
  Button, 
  Grid, 
  Paper,
  Card,
  CardContent,
  CardActions
} from '@mui/material';
import { 
  Upload, 
  Dashboard, 
  Description,
  Speed,
  Security,
  Cloud
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import ROUTES from '@config/routes';

const HomePage = () => {
  const navigate = useNavigate();

  const features = [
    {
      icon: <Speed sx={{ fontSize: 40 }} />,
      title: 'Fast Processing',
      description: 'OCR processing with Tesseract and EasyOCR for quick and accurate results',
    },
    {
      icon: <Security sx={{ fontSize: 40 }} />,
      title: 'High Accuracy',
      description: 'Advanced AI extraction with 99% confidence targeting for reliable data',
    },
    {
      icon: <Description sx={{ fontSize: 40 }} />,
      title: 'Multiple Formats',
      description: 'Support for PDF, JPG, and PNG invoice formats',
    },
  ];

  return (
    <Container maxWidth="lg">
      <Box sx={{ py: 8 }}>
        {/* Hero Section */}
        <Box sx={{ textAlign: 'center', mb: 8 }}>
          <Typography 
            variant="h2" 
            component="h1" 
            gutterBottom
            sx={{ fontWeight: 700 }}
          >
            Invoice Extraction System
          </Typography>
          
          <Typography 
            variant="h5" 
            color="text.secondary" 
            paragraph
            sx={{ mb: 4 }}
          >
            Automated invoice data extraction powered by AI and OCR technology
          </Typography>

          <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center' }}>
            <Button
              variant="contained"
              size="large"
              startIcon={<Upload />}
              onClick={() => navigate(ROUTES.UPLOAD)}
              sx={{ px: 4, py: 1.5 }}
            >
              Upload Invoice
            </Button>
            
            <Button
              variant="outlined"
              size="large"
              startIcon={<Dashboard />}
              onClick={() => navigate(ROUTES.DASHBOARD)}
              sx={{ px: 4, py: 1.5 }}
            >
              View Dashboard
            </Button>
          </Box>
        </Box>

        {/* Features Section */}
        <Grid container spacing={4}>
          {features.map((feature, index) => (
            <Grid item xs={12} md={4} key={index}>
              <Card 
                elevation={2}
                sx={{ 
                  height: '100%',
                  display: 'flex',
                  flexDirection: 'column',
                  transition: 'transform 0.2s',
                  '&:hover': {
                    transform: 'translateY(-4px)',
                    boxShadow: 4,
                  },
                }}
              >
                <CardContent sx={{ flexGrow: 1, textAlign: 'center' }}>
                  <Box 
                    sx={{ 
                      display: 'flex', 
                      justifyContent: 'center', 
                      mb: 2,
                      color: 'primary.main'
                    }}
                  >
                    {feature.icon}
                  </Box>
                  
                  <Typography variant="h5" component="h3" gutterBottom>
                    {feature.title}
                  </Typography>
                  
                  <Typography variant="body2" color="text.secondary">
                    {feature.description}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>

        {/* How It Works Section */}
        <Box sx={{ mt: 8 }}>
          <Typography 
            variant="h4" 
            component="h2" 
            textAlign="center" 
            gutterBottom
            sx={{ mb: 4 }}
          >
            How It Works
          </Typography>

          <Grid container spacing={3}>
            {[
              { step: 1, title: 'Upload Invoice', description: 'Upload your invoice in PDF, JPG, or PNG format' },
              { step: 2, title: 'Select OCR Engine', description: 'Choose between Tesseract or EasyOCR' },
              { step: 3, title: 'Automatic Processing', description: 'AI extracts all relevant data from your invoice' },
              { step: 4, title: 'Review & Export', description: 'Review extracted data and export to your system' },
            ].map((item) => (
              <Grid item xs={12} sm={6} md={3} key={item.step}>
                <Paper 
                  elevation={1} 
                  sx={{ 
                    p: 3, 
                    textAlign: 'center',
                    height: '100%'
                  }}
                >
                  <Box
                    sx={{
                      width: 50,
                      height: 50,
                      borderRadius: '50%',
                      bgcolor: 'primary.main',
                      color: 'white',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: 24,
                      fontWeight: 700,
                      mx: 'auto',
                      mb: 2,
                    }}
                  >
                    {item.step}
                  </Box>
                  
                  <Typography variant="h6" gutterBottom>
                    {item.title}
                  </Typography>
                  
                  <Typography variant="body2" color="text.secondary">
                    {item.description}
                  </Typography>
                </Paper>
              </Grid>
            ))}
          </Grid>
        </Box>

        {/* CTA Section */}
        <Box 
          sx={{ 
            mt: 8, 
            p: 4, 
            bgcolor: 'primary.main', 
            color: 'white',
            borderRadius: 2,
            textAlign: 'center'
          }}
        >
          <Typography variant="h4" gutterBottom>
            Ready to get started?
          </Typography>
          
          <Typography variant="body1" paragraph>
            Upload your first invoice and see the magic of AI-powered data extraction
          </Typography>
          
          <Button
            variant="contained"
            size="large"
            startIcon={<Upload />}
            onClick={() => navigate(ROUTES.UPLOAD)}
            sx={{ 
              bgcolor: 'white', 
              color: 'primary.main',
              '&:hover': {
                bgcolor: 'grey.100',
              },
            }}
          >
            Upload Your First Invoice
          </Button>
        </Box>
      </Box>
    </Container>
  );
};

export default HomePage;