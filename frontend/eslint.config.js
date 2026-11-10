import js from '@eslint/js'
import reactHooks from 'eslint-plugin-react-hooks'
import globals from 'globals'
import tseslint from 'typescript-eslint'

// Feature-Sliced Design: una feature NO importa de otra. Lo transversal vive en shared/ y store/.
// Se listan también las features que se crean en las Fases 2 y 3 para que el límite ya rija.
const FEATURES = [
  'auth',
  'catalogo',
  'carrito',
  'pedidos',
  'direcciones',
  'maestros',
  'inventario',
  'configuracion',
  'dashboard',
]

const crossFeatureRules = FEATURES.map((feature) => ({
  files: [`src/features/${feature}/**/*.{ts,tsx}`],
  rules: {
    'no-restricted-imports': [
      'error',
      {
        patterns: FEATURES.filter((other) => other !== feature).map((other) => ({
          group: [`@/features/${other}`, `@/features/${other}/**`, `**/features/${other}/**`],
          message: `La feature "${feature}" no puede importar de "${other}" (Feature-Sliced Design). Mové lo compartido a shared/ o store/.`,
        })),
      },
    ],
  },
}))

// Las capas inferiores nunca importan de las superiores: páginas → features → hooks y stores → API → tipos.
const layerRules = [
  {
    files: ['src/shared/**/*.{ts,tsx}', 'src/store/**/*.{ts,tsx}'],
    rules: {
      'no-restricted-imports': [
        'error',
        {
          patterns: [
            {
              group: ['@/features/*', '@/pages/*', '@/routes/*'],
              message: 'shared/ y store/ no pueden importar de features, páginas ni rutas.',
            },
          ],
        },
      ],
    },
  },
]

export default tseslint.config(
  { ignores: ['dist', 'node_modules'] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ['**/*.{ts,tsx}'],
    languageOptions: { ecmaVersion: 2022, globals: globals.browser },
    plugins: { 'react-hooks': reactHooks },
    rules: {
      ...reactHooks.configs.recommended.rules,
      // Sin any (rúbrica: "strict: true y sin any").
      '@typescript-eslint/no-explicit-any': 'error',
      '@typescript-eslint/consistent-type-imports': 'error',
      'no-alert': 'error', // nunca window.confirm(): las confirmaciones usan el modal de uiStore
    },
  },
  ...crossFeatureRules,
  ...layerRules,
)
