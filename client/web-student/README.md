# LangBridge Student Client

The **LangBridge Student Client** is a real-time web application designed to provide students with an accessible, localized, and interactive way to follow classroom presentations.

It connects to the LangBridge backend via Firebase Firestore to receive live updates from the presenter's slides, translated into the student's preferred language with synchronized audio.

## 🚀 Features

### 🌐 Real-Time Translation & Synchronization
*   **Live Updates**: As the presenter changes slides, the new content appears instantly on the student's device.
*   **Multi-Language Support**: Students can switch languages on the fly. Language codes follow the **BCP-47** standard used by Google Cloud. Supported languages include:
    *   English (US) (`en-US`)
    *   Chinese (Mandarin - Simplified & Traditional) (`zh-CN`, `zh-TW`)
    *   Cantonese (Hong Kong) (`yue-HK`)
    *   Spanish (`es-ES`)
    *   Japanese (`ja-JP`)
    *   Korean (`ko-KR`)

### 🔊 Smart Audio Player (Text-to-Speech)
*   **Auto-Play**: Automatically plays the audio narration for new slides as they arrive (can be toggled off).
*   **Intelligent Queuing**: Prevents audio overlap by queuing messages to play sequentially.
*   **Interactive Controls**: Play or pause specific messages at any time.

### ♿ Accessibility & UI
*   **Adjustable Font Size**: Easy-to-use `A+` / `A-` controls to adjust text size for better readability.
*   **Mobile-First Design**: Fully responsive layout that works perfectly on smartphones, tablets, and laptops.
*   **Status Indicators**: Clear visual feedback for the connection status (🟢 Live, 🟡 Waiting, 🟠 Connecting).
*   **Context Snippets**: Displays a small preview of the original slide content for reference.

## 🛠️ Tech Stack

*   **Frontend Framework**: [React](https://react.dev/) (v19)
*   **Build Tool**: [Vite](https://vitejs.dev/)
*   **Data & Sync**: [Firebase Firestore](https://firebase.google.com/docs/firestore) (Real-time listeners)
*   **Routing**: React Router

## 🏃‍♂️ Getting Started

### Prerequisites
*   Node.js (v18 or higher)
*   npm

### 1. Installation

Navigate to the project directory and install dependencies:

```bash
cd client/web-student
npm install
```

### 2. Environment Configuration

Create a `.env` file in the `client/web-student` directory with your Firebase configuration (you can find these in your Firebase Console):

```env
VITE_FIREBASE_API_KEY=your_api_key
VITE_FIREBASE_AUTH_DOMAIN=your_project.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your_project_id
VITE_FIREBASE_STORAGE_BUCKET=your_project.appspot.com
VITE_FIREBASE_MESSAGING_SENDER_ID=your_sender_id
VITE_FIREBASE_APP_ID=your_app_id
```

### 3. Run Locally

Start the development server:

```bash
npm run dev
```

Access the app at `http://localhost:5173`.

**URL Parameters:**
To join a specific class/course, append the `class` parameter:
`http://localhost:5173/?class=demo`

(Defaults to `current` if not specified).

### 4. Build & Deploy

Build the application for production:

```bash
npm run build
```

Deploy to Firebase Hosting (ensure you have the Firebase CLI installed and authenticated):

```bash
firebase deploy --only hosting
```

## 📂 Project Structure

*   **`src/App.jsx`**: Main application logic, including Firestore listeners, audio state management, and UI rendering.
*   **`src/firebase.js`**: Firebase initialization and configuration.
*   **`src/index.css`**: Global styles and UI theming.
*   **`firestore.rules`**: Security rules for the database (read-only for students).

## 🔍 Troubleshooting

*   **No Audio**: Most browsers block auto-playing audio until the user has interacted with the page. Click anywhere on the page to enable audio.
*   **"Waiting..." Status**: This means the client is connected but hasn't found an active session for the specified Course ID. Ensure the presenter has started the session.