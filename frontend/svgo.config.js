module.exports = {
  plugins: [
    {
      name: 'preset-default',
      params: {
        overrides: {
          removeViewBox: false,
          removeEmptyAttrs: false,
          cleanupNumericValues: {
            floatPrecision: 2
          },
          convertColors: {
            names2hex: true,
            rgb2hex: true,
            shortname: true,
            shortHex: true
          }
        }
      }
    },
    'removeDimensions',
    {
      name: 'removeAttrs',
      params: {
        attrs: ['data-name', 'data-*']
      }
    }
  ]
};