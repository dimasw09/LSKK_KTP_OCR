const express = require('express');
const app = express();
const port = 3000;

const uploadRoute = require('./src/routes/uploadRoute');
const statusRoute = require('./src/routes/statusRoute');

app.use(express.json());
app.use(express.urlencoded({ extended: false }));

app.use('/', uploadRoute);
app.use('/', statusRoute);

app.listen(port, () => {
  console.log(`Server is running at http://localhost:${port}`);
});
