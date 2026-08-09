import {
  Box,
  Card,
  CardContent,
  Radio,
  RadioGroup,
  FormControlLabel,
  Typography,
  Chip,
} from '@mui/material';
import { Speed, AutoAwesome } from '@mui/icons-material';
import config from '@config/app.config';

const OCRSelector = ({ selectedEngine, onEngineChange, disabled = false }) => {
  const engines = config.ocr.engines;

  const getEngineIcon = (engineId) => {
    if (engineId === 'tesseract') {
      return <Speed />;
    }
    return <AutoAwesome />;
  };

  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        Select OCR Engine
      </Typography>
      
      <Typography variant="body2" color="text.secondary" paragraph>
        Choose the OCR engine for text extraction
      </Typography>

      <RadioGroup value={selectedEngine} onChange={(e) => onEngineChange(e.target.value)}>
        {engines.map((engine) => (
          <Card
            key={engine.id}
            variant="outlined"
            sx={{
              mb: 2,
              cursor: disabled ? 'not-allowed' : 'pointer',
              border: 2,
              borderColor: selectedEngine === engine.id ? 'primary.main' : 'divider',
              bgcolor: selectedEngine === engine.id ? 'primary.lighter' : 'background.paper',
              opacity: disabled ? 0.6 : 1,
              transition: 'all 0.2s ease',
              '&:hover': {
                borderColor: disabled ? 'divider' : 'primary.main',
                boxShadow: disabled ? 'none' : 2,
              },
            }}
            onClick={() => !disabled && onEngineChange(engine.id)}
          >
            <CardContent sx={{ display: 'flex', alignItems: 'flex-start', gap: 2 }}>
              {/* Radio Button */}
              <FormControlLabel
                value={engine.id}
                control={<Radio disabled={disabled} />}
                label=""
                sx={{ m: 0 }}
              />

              {/* Engine Icon */}
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  width: 48,
                  height: 48,
                  borderRadius: 1,
                  bgcolor: selectedEngine === engine.id ? 'primary.main' : 'grey.200',
                  color: selectedEngine === engine.id ? 'white' : 'text.secondary',
                }}
              >
                {getEngineIcon(engine.id)}
              </Box>

              {/* Engine Details */}
              <Box sx={{ flexGrow: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                  <Typography variant="subtitle1" fontWeight={600}>
                    {engine.name}
                  </Typography>
                  {engine.recommended && (
                    <Chip
                      label="Recommended"
                      size="small"
                      color="primary"
                      variant={selectedEngine === engine.id ? 'filled' : 'outlined'}
                    />
                  )}
                </Box>
                <Typography variant="body2" color="text.secondary">
                  {engine.description}
                </Typography>
              </Box>
            </CardContent>
          </Card>
        ))}
      </RadioGroup>

      {/* Info Box */}
      <Box
        sx={{
          mt: 2,
          p: 2,
          bgcolor: 'info.lighter',
          borderRadius: 1,
        }}
      >
        <Typography variant="caption" color="text.secondary">
          💡 <strong>Tip:</strong> Tesseract is faster for printed text and clear documents. 
          EasyOCR works better with handwritten text and complex layouts.
        </Typography>
      </Box>
    </Box>
  );
};

export default OCRSelector;