import type { NextApiRequest, NextApiResponse } from 'next';
import axios from 'axios';
import http from 'http';
import https from 'https';

const BACKEND_URL = process.env.NEXT_PUBLIC_LLM_API_BASE || 'http://localhost:8001';

// Configure API route to handle long-running requests
export const config = {
  api: {
    responseLimit: false,
    bodyParser: {
      sizeLimit: '10mb',
    },
    // Increase timeout for LLM operations (15 minutes for long summary generation)
    externalResolver: true,
  },
};

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  // Disable Next.js default timeout for long-running LLM operations
  // This allows the request to wait up to 15 minutes for backend response (for summary generation)
  if (!res.socket) {
    return res.status(500).json({ error: 'Connection not available' });
  }
  
  // Get the path from the catch-all route
  const { path } = req.query;
  const pathArray = Array.isArray(path) ? path : [path];
  const apiPath = pathArray.join('/');

  // Build the full backend URL
  const backendUrl = `${BACKEND_URL}/${apiPath}`;

  try {
    // Forward the request to the backend
    const response = await axios({
      method: req.method,
      url: backendUrl,
      data: req.body,
      params: Object.fromEntries(
        Object.entries(req.query).filter(([key]) => key !== 'path')
      ), // Filter out 'path' from query params
      headers: {
        'Content-Type': 'application/json',
        ...Object.fromEntries(
          Object.entries(req.headers).filter(([key]) => 
            !['host', 'connection', 'content-length'].includes(key.toLowerCase())
          )
        ),
      },
      timeout: 900000, // 15 minutes timeout for LLM operations (summary generation can take 10+ minutes)
      validateStatus: () => true, // Don't throw on any status
      // Keep connection alive for long-running requests with longer timeout
      httpAgent: new http.Agent({ 
        keepAlive: true, 
        keepAliveMsecs: 120000, // 2 minutes keep-alive
        timeout: 900000, // 15 minutes connection timeout
      }),
      httpsAgent: new https.Agent({ 
        keepAlive: true, 
        keepAliveMsecs: 120000, // 2 minutes keep-alive
        timeout: 900000, // 15 minutes connection timeout
      }),
      // Increase maxContentLength for large responses
      maxContentLength: Infinity,
      maxBodyLength: Infinity,
    });

    // Forward the response
    res.status(response.status).json(response.data);
  } catch (error: any) {
    console.error('API Proxy Error:', error.message);
    console.error('Backend URL:', backendUrl);
    console.error('Error details:', error.response?.data || error.message);
    
    // Provide more detailed error information
    if (error.code === 'ECONNREFUSED') {
      res.status(503).json({ 
        error: 'Backend service unavailable',
        message: 'The backend service is not responding. Please try again later.'
      });
    } else if (error.code === 'ECONNRESET' || error.code === 'EPIPE' || error.message.includes('socket hang up')) {
      // Connection reset during long-running operation - likely timeout or backend still processing
      res.status(504).json({ 
        error: 'Connection reset',
        message: 'The request is taking longer than expected. The backend may still be processing. Please wait a moment and try again, or refresh the page.',
        code: error.code
      });
    } else if (error.code === 'ETIMEDOUT' || error.message.includes('timeout')) {
      res.status(504).json({ 
        error: 'Request timeout',
        message: 'The request took too long to process. Please try again or simplify your query.'
      });
    } else {
      res.status(500).json({ 
        error: 'Failed to proxy request to backend',
        message: error.message,
        code: error.code,
        details: error.response?.data || undefined
      });
    }
  }
}

