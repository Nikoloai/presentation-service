# Firebase Authentication Setup Instructions

## Firebase Configuration Changes

AI SlideRush now uses **Firebase Authentication** instead of Google OAuth. Firebase provides a simpler, more secure authentication flow.

---

## Setup Steps

### 1. Create Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Click "Add project" or select existing project
3. Follow the setup wizard

### 2. Enable Google Sign-In

1. In Firebase Console, go to **Authentication** → **Sign-in method**
2. Enable **Google** provider
3. Add authorized domains if needed

### 3. Get Firebase Config (Frontend)

1. Go to **Project Settings** (gear icon) → **General**
2. Scroll to "Your apps" section
3. Click "Web app" icon (`</>`) to add a web app
4. Copy the Firebase config object

**Edit `static/firebase-auth.js`** and replace the config:

```javascript
const firebaseConfig = {
    apiKey: "YOUR_API_KEY",
    authDomain: "YOUR_PROJECT_ID.firebaseapp.com",
    projectId: "YOUR_PROJECT_ID",
    storageBucket: "YOUR_PROJECT_ID.appspot.com",
    messagingSenderId: "YOUR_MESSAGING_SENDER_ID",
    appId: "YOUR_APP_ID"
};
```

### 4. Get Service Account Key (Backend)

1. In Firebase Console, go to **Project Settings** → **Service accounts**
2. Click **"Generate new private key"**
3. Save the JSON file as `serviceAccountKey.json` in your project root

**Add to `.env`**:
```
FIREBASE_SERVICE_ACCOUNT_KEY=serviceAccountKey.json
```

⚠️ **IMPORTANT**: Add `serviceAccountKey.json` to `.gitignore` to prevent committing secrets!

### 5. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs `firebase-admin` and removes `Authlib`.

### 6. Run the Application

```bash
python app.py
```

Firebase authentication is now active!

---

## Migration Notes

### Removed:
- ❌ `Authlib` package
- ❌ `/auth/google` and `/auth/google/callback` routes
- ❌ `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` environment variables
- ❌ Google OAuth configuration in Flask

### Added:
- ✅ `firebase-admin` package
- ✅ `/auth/firebase/` API endpoint for token verification
- ✅ `firebase_uid` column in users table
- ✅ `get_or_create_firebase_user()` helper function
- ✅ Frontend Firebase SDK integration
- ✅ `static/firebase-auth.js` for Google Sign-In

### Database Changes:
- New column: `firebase_uid` (automatically added via migration)
- Existing users with email/password continue to work
- Firebase users can be linked to existing email accounts

---

## Testing

1. Open login page: `http://localhost:5000/login`
2. Click "Sign in with Firebase/Google"
3. Firebase popup appears → Sign in with Google
4. Backend verifies token and logs user in
5. Redirected to dashboard

---

## Troubleshooting

**"Firebase not configured" error**:
- Ensure `firebase-auth.js` has correct config (not placeholder values)
- Check browser console for Firebase initialization errors

**"Invalid token" error**:
- Verify `serviceAccountKey.json` is correct
- Ensure `FIREBASE_SERVICE_ACCOUNT_KEY` path in `.env` is correct
- Check Firebase project ID matches

**Button stays disabled**:
- Firebase config is not set (still using placeholder values)
- Check browser console for import errors
- Ensure internet connection for Firebase CDN

---

## Security Notes

- 🔐 Service account key has admin access — **NEVER commit to Git**
- 🔐 Add to `.gitignore`: `serviceAccountKey.json`
- 🔐 Keep Firebase API key public (it's safe for frontend)
- 🔐 Backend validates all tokens server-side
- 🔐 Use environment variables for production

---

## Next Steps

After setup:
1. Test sign-in flow
2. Check user creation in database
3. Verify dashboard access
4. Test sign-out
5. Deploy to production (set env variables properly)

For production deployment:
- Use environment variables for `FIREBASE_SERVICE_ACCOUNT_KEY`
- Store service account key as base64-encoded secret
- Configure authorized domains in Firebase Console

---

## Support

If you encounter issues:
1. Check Firebase Console → Authentication logs
2. Check backend terminal for error messages
3. Check browser console for frontend errors
4. Verify all config values are correct
