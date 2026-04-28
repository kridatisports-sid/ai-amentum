// src/utils/firebase.js
// Initialise Firebase client SDK from env variables

import { initializeApp } from 'firebase/app'
import { getAuth, GoogleAuthProvider, signInWithPopup, signOut } from 'firebase/auth'

const firebaseConfig = {
  apiKey:            import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain:        import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId:         import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket:     import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId:             import.meta.env.VITE_FIREBASE_APP_ID,
}

const app  = initializeApp(firebaseConfig)
export const auth = getAuth(app)

// ── Auth helpers ──────────────────────────────────────────────────────────────

export const signInWithGoogle = () =>
  signInWithPopup(auth, new GoogleAuthProvider())

export const signOutUser = () => signOut(auth)

export const getIdToken = async () => {
  const user = auth.currentUser
  if (!user) return null
  return user.getIdToken()
}
