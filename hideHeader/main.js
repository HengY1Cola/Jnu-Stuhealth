// 来自小透明 https://akarin.dev/2022/02/15/disable-geckodriver-detection-with-addon/
delete window.navigator.wrappedJSObject.__proto__.webdriver;
