{
  "version": 2,
  "routes": [
    {
      "src": "/dados/(.*)",
      "dest": "/dados/$1"
    },
    {
      "handle": "filesystem"
    },
    {
      "src": "/.*",
      "dest": "/index.html"
    }
  ]
}
