//'use strict';

// --- INIT
var gulp 			  = require("gulp"),
	minifyHTML		= require("gulp-minify-html"),
  plumber       = require('gulp-plumber'),
  gutil         = require('gulp-util'),
	//jshint			= require("gulp-jshint"),
	less 			    = require("gulp-less"),
	//sourcemaps		= require("gulp-sourcemaps"),
	autoprefix		= require("gulp-autoprefixer"),
	rename 			  = require('gulp-rename'),
	minify 			  = require('gulp-minify-css'), // minifies CSS
	concat 			  = require('gulp-concat'),
    uglify 			= require('gulp-uglify'); // minifies JS

// Paths variables
var paths = {
	'dev': {
        'less': 'public/dev/less/',
        'js': 'public/dev/js/',
        'vendor': 'public/dev/vendor/'
    },
    'assets': {
        'css': 'public/assets/css/',
        'js': 'public/assets/js/',
        'vendor': 'public/assets/bower_vendor/'
    }
}

// --- TASKS
// CSS
gulp.task('css', function() {  
  // place code for your default task here
  return gulp.src(paths.dev.less+'app.less') // get file
    .pipe(plumber(function(error) {
            gutil.log(gutil.colors.red(error.message));
            this.emit('end');
        }))
    .pipe(less())
    .pipe(gulp.dest(paths.assets.css)) // output: app.css
    .pipe(autoprefix('last 2 version', 'ie 8', 'ie 9'))
    .pipe(minify({keepSpecialComments:0}))
    .pipe(rename({suffix: '.min'}))
    .pipe(gulp.dest(paths.assets.css)); // output: app.min.css
});

// JS
gulp.task('js', function(){  
  return gulp.src([
      paths.assets.vendor+'jquery/dist/jquery.js',
      paths.assets.vendor+'bootstrap/dist/js/bootstrap.js',
      paths.dev.js+'app.js'
    ])
	//.pipe(jshint())
	//.pipe(jshint.reporter('default'))
    .pipe(concat('app.min.js'))
    .pipe(uglify())
    .pipe(gulp.dest(paths.assets.js));
});

// --- WATCH
//Rerun the task when a file changes
gulp.task('watch', function() { 
	gulp.watch(paths.dev.less+'*', ['css']);
  
	gulp.watch(paths.dev.js+'*', ['js']);
});

// --- DEFAULT
gulp.task('default', ['css', 'js', 'watch']);