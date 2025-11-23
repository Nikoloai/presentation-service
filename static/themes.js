// Theme definitions for AI SlideRush
const themes = {
    light: {
        name: 'Light',
        colors: {
            primary: '#667eea',
            primaryDark: '#5568d3',
            secondary: '#764ba2',
            background: '#ffffff',
            surface: '#f8f9fa',
            text: '#333333',
            textSecondary: '#666666',
            border: '#e0e0e0',
            success: '#11998e',
            error: '#ff6b6b',
            headerBg: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            buttonPrimary: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            buttonSuccess: 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)'
        }
    },
    
    dark: {
        name: 'Dark',
        colors: {
            primary: '#bb86fc',
            primaryDark: '#9965f4',
            secondary: '#03dac6',
            background: '#121212',
            surface: '#1e1e1e',
            text: '#ffffff',
            textSecondary: '#b0b0b0',
            border: '#2d2d2d',
            success: '#03dac6',
            error: '#cf6679',
            headerBg: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
            buttonPrimary: 'linear-gradient(135deg, #bb86fc 0%, #9965f4 100%)',
            buttonSuccess: 'linear-gradient(135deg, #03dac6 0%, #00b4a6 100%)'
        }
    },
    
    modern: {
        name: 'Modern',
        colors: {
            primary: '#4f46e5',
            primaryDark: '#4338ca',
            secondary: '#06b6d4',
            background: '#fafafa',
            surface: '#ffffff',
            text: '#0f172a',
            textSecondary: '#475569',
            border: '#e2e8f0',
            success: '#10b981',
            error: '#ef4444',
            headerBg: 'linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)',
            buttonPrimary: 'linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)',
            buttonSuccess: 'linear-gradient(135deg, #10b981 0%, #059669 100%)'
        }
    },
    
    casual: {
        name: 'Casual',
        colors: {
            primary: '#ff6b9d',
            primaryDark: '#ff4d8a',
            secondary: '#ffa07a',
            background: '#fff5f7',
            surface: '#ffffff',
            text: '#333333',
            textSecondary: '#666666',
            border: '#ffd6e0',
            success: '#6bcf7f',
            error: '#ff6b6b',
            headerBg: 'linear-gradient(135deg, #ff6b9d 0%, #c44569 100%)',
            buttonPrimary: 'linear-gradient(135deg, #ff6b9d 0%, #c44569 100%)',
            buttonSuccess: 'linear-gradient(135deg, #6bcf7f 0%, #51cf66 100%)'
        }
    },
    
    classic: {
        name: 'Classic',
        colors: {
            primary: '#2c3e50',
            primaryDark: '#1a252f',
            secondary: '#34495e',
            background: '#ecf0f1',
            surface: '#ffffff',
            text: '#2c3e50',
            textSecondary: '#7f8c8d',
            border: '#bdc3c7',
            success: '#27ae60',
            error: '#e74c3c',
            headerBg: 'linear-gradient(135deg, #2c3e50 0%, #34495e 100%)',
            buttonPrimary: 'linear-gradient(135deg, #2c3e50 0%, #34495e 100%)',
            buttonSuccess: 'linear-gradient(135deg, #27ae60 0%, #229954 100%)'
        }
    },
    
    futuristic: {
        name: 'Futuristic',
        colors: {
            primary: '#00d4ff',
            primaryDark: '#00a8cc',
            secondary: '#ff00ff',
            background: '#0a0e27',
            surface: '#151b3d',
            text: '#ffffff',
            textSecondary: '#8892b0',
            border: '#1e2749',
            success: '#00ff88',
            error: '#ff0055',
            headerBg: 'linear-gradient(135deg, #0a0e27 0%, #1e2749 100%)',
            buttonPrimary: 'linear-gradient(135deg, #00d4ff 0%, #0099cc 100%)',
            buttonSuccess: 'linear-gradient(135deg, #00ff88 0%, #00cc6a 100%)'
        }
    },
    
    minimal: {
        name: 'Minimal',
        colors: {
            primary: '#000000',
            primaryDark: '#1a1a1a',
            secondary: '#666666',
            background: '#ffffff',
            surface: '#f5f5f5',
            text: '#000000',
            textSecondary: '#666666',
            border: '#dddddd',
            success: '#000000',
            error: '#000000',
            headerBg: 'linear-gradient(135deg, #000000 0%, #333333 100%)',
            buttonPrimary: 'linear-gradient(135deg, #000000 0%, #1a1a1a 100%)',
            buttonSuccess: 'linear-gradient(135deg, #333333 0%, #1a1a1a 100%)'
        }
    },
    
    gradient: {
        name: 'Gradient',
        colors: {
            primary: '#f093fb',
            primaryDark: '#e878f5',
            secondary: '#4facfe',
            background: '#fef9ff',
            surface: '#ffffff',
            text: '#333333',
            textSecondary: '#666666',
            border: '#f0e6f6',
            success: '#43e97b',
            error: '#fa709a',
            headerBg: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
            buttonPrimary: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
            buttonSuccess: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)'
        }
    },
    
    glassmorphism: {
        name: 'Glassmorphism',
        colors: {
            primary: 'rgba(255, 255, 255, 0.25)',
            primaryDark: 'rgba(255, 255, 255, 0.4)',
            secondary: 'rgba(120, 119, 198, 0.3)',
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            surface: 'rgba(255, 255, 255, 0.1)',
            text: '#ffffff',
            textSecondary: 'rgba(255, 255, 255, 0.8)',
            border: 'rgba(255, 255, 255, 0.2)',
            success: 'rgba(56, 239, 125, 0.3)',
            error: 'rgba(255, 107, 107, 0.3)',
            headerBg: 'rgba(255, 255, 255, 0.1)',
            buttonPrimary: 'rgba(255, 255, 255, 0.25)',
            buttonSuccess: 'rgba(56, 239, 125, 0.25)'
        },
        special: {
            backdropFilter: 'blur(10px)',
            borderGlass: '1px solid rgba(255, 255, 255, 0.2)',
            boxShadow: '0 8px 32px 0 rgba(31, 38, 135, 0.37)'
        }
    },
    
    nature: {
        name: 'Nature',
        colors: {
            primary: '#2d6a4f',
            primaryDark: '#1b4332',
            secondary: '#95d5b2',
            background: '#f1faee',
            surface: '#ffffff',
            text: '#1b4332',
            textSecondary: '#52b788',
            border: '#d8f3dc',
            success: '#40916c',
            error: '#e63946',
            headerBg: 'linear-gradient(135deg, #2d6a4f 0%, #52b788 100%)',
            buttonPrimary: 'linear-gradient(135deg, #2d6a4f 0%, #40916c 100%)',
            buttonSuccess: 'linear-gradient(135deg, #52b788 0%, #74c69d 100%)'
        }
    },
    
    vivid: {
        name: 'Vivid',
        colors: {
            primary: '#ff006e',
            primaryDark: '#d90059',
            secondary: '#fb5607',
            background: '#fffcf2',
            surface: '#ffffff',
            text: '#212529',
            textSecondary: '#495057',
            border: '#ffbe0b',
            success: '#06ffa5',
            error: '#ff006e',
            headerBg: 'linear-gradient(135deg, #ff006e 0%, #fb5607 100%)',
            buttonPrimary: 'linear-gradient(135deg, #ff006e 0%, #fb5607 100%)',
            buttonSuccess: 'linear-gradient(135deg, #06ffa5 0%, #00cc83 100%)'
        }
    },
    
    business: {
        name: 'Business',
        colors: {
            primary: '#1e3a8a',
            primaryDark: '#1e40af',
            secondary: '#0ea5e9',
            background: '#f8fafc',
            surface: '#ffffff',
            text: '#0f172a',
            textSecondary: '#475569',
            border: '#cbd5e1',
            success: '#059669',
            error: '#dc2626',
            headerBg: 'linear-gradient(135deg, #1e3a8a 0%, #1e40af 100%)',
            buttonPrimary: 'linear-gradient(135deg, #1e3a8a 0%, #1e40af 100%)',
            buttonSuccess: 'linear-gradient(135deg, #059669 0%, #047857 100%)'
        }
    }
};

// Theme names in different languages
const themeNames = {
    en: {
        light: 'Light',
        dark: 'Dark',
        modern: 'Modern',
        casual: 'Casual',
        classic: 'Classic',
        futuristic: 'Futuristic',
        minimal: 'Minimal',
        gradient: 'Gradient',
        glassmorphism: 'Glassmorphism',
        nature: 'Nature',
        vivid: 'Vivid',
        business: 'Business'
    },
    es: {
        light: 'Clara',
        dark: 'Oscura',
        modern: 'Moderna',
        casual: 'Casual',
        classic: 'Clásica',
        futuristic: 'Futurista',
        minimal: 'Minimalista',
        gradient: 'Degradado',
        glassmorphism: 'Cristal',
        nature: 'Naturaleza',
        vivid: 'Vívida',
        business: 'Negocios'
    },
    ru: {
        light: 'Светлая',
        dark: 'Тёмная',
        modern: 'Современная',
        casual: 'Повседневная',
        classic: 'Классическая',
        futuristic: 'Футуристичная',
        minimal: 'Минималистичная',
        gradient: 'Градиентная',
        glassmorphism: 'Гласморфизм',
        nature: 'Природная',
        vivid: 'Яркая',
        business: 'Бизнес'
    },
    zh: {
        light: '浅色',
        dark: '深色',
        modern: '现代',
        casual: '休闲',
        classic: '经典',
        futuristic: '未来',
        minimal: '极简',
        gradient: '渐变',
        glassmorphism: '玻璃',
        nature: '自然',
        vivid: '鲜艳',
        business: '商务'
    },
    fr: {
        light: 'Clair',
        dark: 'Sombre',
        modern: 'Moderne',
        casual: 'Décontracté',
        classic: 'Classique',
        futuristic: 'Futuriste',
        minimal: 'Minimaliste',
        gradient: 'Dégradé',
        glassmorphism: 'Verre',
        nature: 'Nature',
        vivid: 'Vif',
        business: 'Affaires'
    }
};

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { themes, themeNames };
}
