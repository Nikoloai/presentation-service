// Firebase Authentication Module
// Initialize Firebase App with your config

// TODO: Replace with your Firebase config from Firebase Console
const firebaseConfig = {
    apiKey: "AIzaSyDnRZ_aFl8FotFa3QzW2SwBft__Hhzihz4",
    authDomain: "sliderush-13d84.firebaseapp.com",
    projectId: "sliderush-13d84",
    storageBucket: "sliderush-13d84sliderush-13d84.firebasestorage.app",
    messagingSenderId: "512491560328",
    appId: "1:512491560328:web:794617bcc34d801d77ae3d"
};

// Check if Firebase config is set
const isFirebaseConfigured = firebaseConfig.apiKey !== "YOUR_API_KEY";

// Initialize Firebase only if configured
let auth = null;
let googleProvider = null;

if (isFirebaseConfigured) {
    // Import Firebase modules dynamically
    import('https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js')
        .then(({ initializeApp }) => {
            import('https://www.gstatic.com/firebasejs/10.7.1/firebase-auth.js')
                .then(({ getAuth, GoogleAuthProvider, signInWithPopup }) => {
                    // Initialize Firebase
                    const app = initializeApp(firebaseConfig);
                    auth = getAuth(app);
                    googleProvider = new GoogleAuthProvider();
                    console.log('✅ Firebase initialized successfully');
                    
                    // Enable Google sign-in button
                    const googleBtn = document.getElementById('googleSignInBtn');
                    if (googleBtn) {
                        googleBtn.disabled = false;
                        googleBtn.classList.remove('disabled');
                    }
                })
                .catch(err => console.error('Firebase Auth import error:', err));
        })
        .catch(err => console.error('Firebase App import error:', err));
} else {
    console.warn('⚠️ Firebase not configured. Please add your Firebase config in firebase-auth.js');
}

// Google Sign-In function
async function signInWithGoogle() {
    if (!auth || !googleProvider) {
        alert('Firebase authentication is not configured. Please contact the administrator.');
        return;
    }
    
    try {
        // Show loading
        const btn = document.getElementById('googleSignInBtn');
        const originalText = btn.innerHTML;
        btn.innerHTML = '⏳ Signing in...';
        btn.disabled = true;
        
        // Import signInWithPopup dynamically
        const { signInWithPopup } = await import('https://www.gstatic.com/firebasejs/10.7.1/firebase-auth.js');
        
        // Sign in with Google popup
        const result = await signInWithPopup(auth, googleProvider);
        
        // Get ID token
        const idToken = await result.user.getIdToken();
        
        // Send token to backend
        const response = await fetch('/auth/firebase/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ token: idToken })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            // Redirect to dashboard
            window.location.href = data.redirect || '/dashboard';
        } else {
            throw new Error(data.error || 'Authentication failed');
        }
        
    } catch (error) {
        console.error('Google Sign-In Error:', error);
        
        // Restore button
        const btn = document.getElementById('googleSignInBtn');
        btn.innerHTML = originalText;
        btn.disabled = false;
        
        // Show error message
        if (error.code === 'auth/popup-closed-by-user') {
            alert('Sign-in cancelled');
        } else {
            alert('Sign-in failed: ' + (error.message || 'Unknown error'));
        }
    }
}

// Attach to global scope for onclick handler
window.signInWithGoogle = signInWithGoogle;
