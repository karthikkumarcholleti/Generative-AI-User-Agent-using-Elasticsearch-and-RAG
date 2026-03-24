#!/usr/bin/env python3
"""
Simple HTTP server to serve the frontend HTML file.
Run this to test the frontend interface.
"""

import http.server
import socketserver
import os
import sys

PORT = 5173

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

if __name__ == "__main__":
    # Change to the directory containing this script
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
        print(f"Frontend server running at http://localhost:{PORT}")
        print("Open your browser and navigate to the above URL to access the FHIR LLM interface.")
        print("Press Ctrl+C to stop the server.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")
            sys.exit(0)
