---
pic     : android-dev
layout  : post
title   : Android Development from the Command Line
author  : Gabriele N. Tornetta
date    : 2017-10-14 22:42:00 +0100
github  : P403n1x87/androtest
toc     : true

categories:
  - Android
  - Java
  - Gradle

tags:
  - Programming
  - Java
  - Android
  - Gradle
  - Lint

excerpt: >
  Do you like your development tools to be as simple as a text editor to write the code and a bunch of CLI application to build your projects? Do you feel like you are in a cage when you use an IDE? Or perhaps your PC or laptop is a bit dated and all the cores spin like crazy when you fire up Android Studio? Then read on to learn how you can develop Android application with just the text editor of your choice and the standard Android SDK CLI tools.
---

# Introduction

Yes you guessed it right, I'm not a huge fan of IDEs. Don't get me wrong though, I am fully aware of how powerful modern IDEs are, and all the magic that they can do for you to assist you while you are coding your application. But this is also why I don't like them, especially when I'm picking up something new.

To the date of writing, I am not an experienced Android developer. When I started developing applications (there was a time when I believed that no matter how big a project could be, you could always find the time to code it in assembly language), a plain old text editor was my friend, together with some command line tools, like assemblers, linkers, compilers, debuggers etc.... With no support at all, you had to know exactly what you were doing, you had to know the syntax, the APIs and where they were located. You also needed a minimum knowledge of what a linker is for and when and why you need one.

Whenever I tried an IDE, e.g. Android Studio, I always felt like I didn't really need to know much about the frameworks I was using, as all the built-in tools would come to my rescue. As a consequence, I started feeling like I wasn't really mastering anything and put the project I was working on aside for future me to one day resume working on it. Rather than me using the IDE, it kind of was the other way around: the IDE was using me to magically generate code.

IDEs also tend to hide all the machinery involved in the build process from the developer as well. In most cases, everything goes well, but what would you do if you suddenly come across a problem and you have no clue at which stage of the build process it is happening?

Surely, if you work on a big company project, it would be crazy to renounce entirely to IDEs, as your life might be a bit harder in everyday maintenance of your code, but for smaller projects this argument is somewhat weak, and opting for a plain text editor might have its many advantages. For once, you are in total control of the code that is going into your final product. And then again, there is also the educational aspect, which can give you the right amount of experience to tackle unexpected issues that could pop up during any stage of the development life-cycle.

All this being said, in this post we shall see how to develop an Android application by only relying on a text editor of your choice and the standard CLI tool provided by the Android SDK. The focus is on the steps required to install the Android SDK command line tools and how to organise your source code, rather than on the details of the application itself.

As with a standard Android project created with Android Studio, we are going to rely on Gradle and the Android Gradle plugin for the build process. You may rightfully think that this somehow partly defeats the point of this post, but, hey, in the end Gradle is just a command line tool, and quite a standard way to build and deploy Java projects these days.

This post is targeted to Linux users, but there is a good chance that the steps that we will go through have an equivalent on other platforms, like Windows. I'm afraid this is something that you will have to find out on your own.

Code very similar to the one presented in this post can be found in the GitHub repository [androtest](https://www.github.com/{{ page.github }}).

# Pre-requisites

Before embarking on an adventure, it is wise to check that we are taking all that we need along the way with us. As we are trying to keep things as simple as possible, we won't need much, but there are a few preliminary steps that we need to perform in order to set up our development environment.

The first few steps couldn't be simpler: pick your favourite text editor (my laptop can still handle an application like Atom) and terminal application, and we already have almost half of what we need! The rest of the tools is provided by the Java Development Kit, the Android SDK Tools and Gradle. More details in due time.

The JDK is usually available from your distro's repositories. On Ubuntu, it can be installed with, e.g.

{% terminal $ %}
sudo apt install openjdk-9-jdk
{% endterminal %}

The Android SDK might not be available from the official repositories. In principle the could be installed along with Android Studio, but if you are not going to use Google's official IDE then it is a bit of waste of space. The _cleaner_ alternative is to just download the Android SDK Tools from the [Android Studio](https://developer.android.com/studio/index.html#command-tools) download page. For simplicity, I will split the installation process of the Android SDK into different steps.

## Android SDK Tools

Download the zip archive and extract it somewhere, e.g. `~/.android/sdk`, then update your `.bashrc` file to define the `ANDROID_HOME` environment variable and include the SDK tools binaries in the `PATH` variable by adding the following lines

{% highlight shell %}
# Android SDK Tools
export ANDROID_HOME=$HOME/.android/sdk
export PATH=$PATH:$ANDROID_HOME/tools:$ANDROID_HOME/tools/bin
{% endhighlight %}

Note that most of the tools installed in `$ANDROID_HOME/tools` are deprecated and one should use the dedicated ones provided in the `$ANDROID_HOME/tools/bin` folder. These include the fundamental [`sdkmanager`](https://developer.android.com/studio/command-line/sdkmanager.html) and the [`avdmanager`](https://developer.android.com/studio/command-line/avdmanager.html) tools for respectively creating and managing different SDK versions (and other packages too) and virtual devices (the emulators).

## Android SDK Platform Tools

Throughout the Android development life-cycle, you are likely to need to interface with the Android platform for testing your progress. In concrete terms this means that you might want to compile your project as you develop it for testing on an actual Android device. In order to connect to the device and look at the log you will need the Android Debug Bridge, which is provided with the Android Platform Tools. To install them we can use the `sdkmanager` CLI tool to pull the latest released version with the following command

{% terminal $ %}
sdkmanager "platform-tools"
{% endterminal %}

This will install the Platform Tools into the `$ANDROID_HOME/platform-tools` folder. We can then add it to the `PATH` variable for easy invocation by simply adding the following lines to `.bashrc`

{% highlight shell %}
# Android Platform Tools
export PATH=$PATH:$ANDROID_HOME/platform-tools
{% endhighlight %}


## Android SDK Platforms

In order to compile a project we need a certain API revision to be installed. This provides all the functionalities that our application can use and are provided in the form of Java packages and classes and other useful components. For example, if our project targets Marshmallow, then we need to install the Android SDK Platform API Level 23. You can find out more at [this page](https://developer.android.com/guide/topics/manifest/uses-sdk-element.html#ApiLevels). To find out about all the packages available to download we can use the command

{% terminal $ %}
sdkmanager --list --verbose
{% endterminal %}

At the moment we are interested in Android platforms, i.e. those packages that are prefixed with `platforms;`, so we can filter the output of the above command as follows

{% terminal $ %}
sdkmanager --list --verbose | grep -A 3 platforms\;
{% endterminal %}

Among the matching results, you should see something similar to the following

{% terminal %}
platforms;android-23
    Description:        Android SDK Platform 23
    Version:            3
{% endterminal %}

We can then proceed to installing the Android SDK Platform API Level 23 with the command

{% terminal $ %}
sdkmanager "platforms;android-23"
{% endterminal %}

> When you use the `sdkmanager` tool, you might see the following warning message
>
> `Warning: File /home/user/.android/repositories.cfg could not be loaded.`
>
> In order to get rid of it you can simply create this file with no content.

## Android SDK Build Tools

Now that we have the API to compile against, we need the tools to actually be able to build a project: the build tools. They provide utilities like `apksigner`, Jack and Jill etc..., but for the moment we don't have to worry about the details of this package, as they will be invoked behind the scenes by Gradle.

The [Android Studio User Guide](https://developer.android.com/studio/releases/build-tools.html) recommends that you keep the build tools updated to the latest version. To find out all the versions available for download, run the following command

{% terminal $ %}
sdkmanager --list --verbose | grep -A 3 build-tools\;
{% endterminal %}

and locate the latest version. At the moment of writing this is 26.0.1, so the command to use in this case is

{% terminal $ %}
sdkmanager "build-tools;26.0.1"
{% endterminal %}

## Android Emulator

The installation of the Android Emulator package is not mandatory, as you can decide to test your application on an actual Android device. However, there are many reasons why you might want to use an emulator: you probably don't own a huge variety of Android devices, differing not only in physical size, but also in the API version (Kit Kat, Lollipop, Marshmallow, just to name a few of the most recent code-names). The package can be installed through the `sdkmanger` with the command

{% terminal $ %}
sdkmanager "emulator"
{% endterminal %}

Again, we can add the emulator folder to the `PATH` variable for easy access. However, the Android SDK Tools provides a deprecated set of tools, `emulator` and `emulator-check`, that would collide with the ones we have just installed. To solve this problem we can rename the deprecated executables with

{% terminal $ %}
chmod -x $ANDROID_HOME/tools/emulator
chmod -x $ANDROID_HOME/tools/emulator-check
mv $ANDROID_HOME/tools/emulator $ANDROID_HOME/tools/emulator.dep
mv $ANDROID_HOME/tools/emulator-check $ANDROID_HOME/tools/emulator-check.dep
{% endterminal %}

and then add the others to the `PATH` variables by appending the following lines to the `~/.bashrc` file

{% highlight shell %}
# Android Emulator
export PATH=$PATH:$ANDROID_HOME/emulator
{% endhighlight %}

## Gradle

Let's now proceed to the installation of Gradle, a build automation system that is also the default in Android Studio. Google has developed a dedicated Android plugin to assist with the most common tasks. The ones that I personally tend to run more frequently are collected in the following table

| **Task** | **Description** |
| -------- | --------------- |
| `compileDebugJavaWithJavac` | Compiles the debug version of the java sources. Useful to check for syntax errors while coding |
| `installDebug ` | Compiles and installs the debug version on all the devices discovered by the ADB.
| `lint` | Runs a lint on the sources, producing a report in `build/reports`.

Gradle is quite popular so it should be available from your distro's official repositories. On Ubuntu 17.04 though, a quite old version of Gradle is available from them, so I would recommend that you add [Cheng-Wei Chien's  PPA](https://launchpad.net/~cwchien/+archive/ubuntu/gradle) to your software sources and install Gradle from there

{% terminal $ %}
sudo add-apt-repository ppa:cwchien/gradle
sudo apt update && sudo apt install gradle
{% endterminal %}

Gradle is quite a powerful tool, but you might find that it has a rather steep learning curve to master all of its features, especially if you are not familiar with Groovy. In this post we shall only scratch the very surface and look at only the closures that we need for this project, as a discussion on Gradle surely deserves a dedicated post on its own.

Getting back on business, the installation of Gradle was the last step that we needed to perform in order to set up the development environment, and we can now move on to creating an Android project from scratch.


# Creating the Gradle Project

The first thing to do is to create a Gradle project of Java type. This involves setting up a directory structure in the project's parent folder and creating the Gradle build script `build.gradle`. With Gradle installed, these steps can be automated with the [`init`](https://docs.gradle.org/current/userguide/build_init_plugin.html) task

{% terminal $ %}
gradle init --type java-library
{% endterminal %}

If you are contributing to a project that is the work of many hands, it will probably be the case that everybody is using the same build tools. As everybody can have a different version of Gradle on their local machine, the Gradle project recommends that one uses a [wrapper](https://docs.gradle.org/current/userguide/gradle_wrapper.html) to build a project, rather than invoke the local installation of Gradle directly. By sharing the wrapper along with your project, every other developer working on the same project will be able to use the same version of Gradle as everybody else, thus getting rid of problems caused by switching between different versions. Even though this is a sample project, we will nonetheless create and use a Gradle wrapper to build our project. The previous command should have created a `gradlew` shell script in the project's folder. If not, run the following command

{% terminal $ %}
gradle wrapper
{% endterminal %}

You should also have a folder `src/` containing all the sub-folders where Gradle expects the sources and the resources that make up your project. But, most importantly, you should also have the `build.gradle` and `settings.gradle` files containing some sample build settings. This structure is slightly different from the one generated by Android Studio, and documented on the [developer portal](https://developer.android.com/studio/build/index.html), where you can notice a nested Gradle project, with the topmost one used to import the actual project as a module, and configure the global build settings. For the case at hand, we could to without this nested structure and only define a single build script, since our project is made up of only one module.

The following is the content of the `build.gradle` file.

{% highlight groovy %}
buildscript {
    repositories {
        jcenter()
    }
    dependencies {
        classpath 'com.android.tools.build:gradle:2.3.3'
    }
}

apply plugin: 'com.android.application'

android {
    compileSdkVersion 23
    buildToolsVersion '26.0.1'
}
{% endhighlight %}

You can find a detailed explanation of the meaning of each closure in the [Configure Your Build](https://developer.android.com/studio/build/index.html#top-level) page of the Android Developer portal. Briefly, the `buildscript` closure is used to configure Gradle itself so that it knows where to find the Android-specific Gradle tools that we want to use. We can then import the Android Gradle plugin and use the extensions to the DSL that it provides to configure the Android-specific build process. In this case we specify that the compilation SDK version that we want to use is Level 23 (Marshmallow), and that we want to use the version `26.0.1` of the build tools.

The `gradle.properties` file is used to configure the project-wide Gradle settings, such as the Gradle daemon's maximum heap size. In fact, this is all we will use it for in our case. Open it with your text editor and put the following content in it

{% highlight groovy %}
org.gradle.jvmargs=-Xmx1536m
{% endhighlight %}

This is our Gradle project created and configured! All the magic of the building process is hidden from us by the Android Gradle plugin so that we don't have to worry about anything else and just focus on our application code.


# Writing the Application

Two essential ingredients for an Android application are the **Main Activity** and the [**App Manifest**](https://developer.android.com/guide/topics/manifest/manifest-intro.html). Let's start with the latter first.

## The Application Manifest

The Android Application Manifest is an XML manifest file that is used to provide the Android system with essential information of an application, like the name of the Java package, the activities provided, the permissions required, the minimum SDK version supported etc... . Within a Gradle project, this file must be located in the `src/main` folder and named rigorously `AndroidManifest.xml`. In our case, this is what such manifest file would look like

{% highlight xml %}
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
  package="com.p403n1x87.androtest">

  <uses-sdk
    android:minSdkVersion="21"
    android:targetSdkVersion="23" />

  <application
    android:label="AndroTest"
    android:theme="@android:style/Theme.Material">

    <activity android:name="MainActivity">
      <intent-filter>
        <action android:name="android.intent.action.MAIN" />
        <category android:name="android.intent.category.LAUNCHER" />
      </intent-filter>
    </activity>
  </application>
</manifest>

{% endhighlight %}

The structure of the Android Application Manifest file is described [on the developer portal](https://developer.android.com/guide/topics/manifest/manifest-intro.html#filestruct) in the form of a skeleton, as it is not based on any XML schema like DTD or XSD.

The root element is `manifest`, which accepts the `package` attribute. Here we specify the name of the Java package of our application. We also specify our target API level to 23. The minimum level supported is set to 21 for reasons that relate to the output of the `lint` Android Gradle task that we will look at later on. It is recommended that you set this attribute to a reasonable value. For example, if you do not set it, Android will automatically add the legacy overflow _three-dot_ button, even though there are no actions to show. Starting from level 11, Android does not add this button by default.

The `manifest` element must contain a unique `application` element that describes our application in may aspects, from the theme to use, to the activity content. In this case we set the application name to `AndroTest` and the theme to `Material` and we expose only one activity, i.e. the `MainActivity`, which is the entry point of our application, and the one that would be fired up when we launch it.

## The Main Activity

This takes us now to the main activity, i.e. the Java class that contains the code to be executed when our application is launched. Within a Gradle project, the main Java code should reside in the `src/main/java` folder. Since the package name is `com.p403n1x87.androtest`, the `MainActivity.java` source file should be created within the `src/main/java/com/p403n1x87/androtest` folder. Here is the code

{% highlight java linenos %}
package com.p403n1x87.androtest;

import android.app.Activity;
import android.os.Bundle;

import android.content.Context;

import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;

import android.view.ViewGroup.LayoutParams;

import android.widget.TextView;
import android.widget.LinearLayout;

import java.util.List;

import static java.lang.Math.sqrt;


public class MainActivity extends Activity
{
  private SensorManager mSensorManager;
  private Sensor        mSensor;

  private TextView      text       = null;
  private LinearLayout  layoutMain = null;

  @Override
  public void onCreate(Bundle savedInstanceState) {
    super.onCreate(savedInstanceState);

    // UI
    setContentView(R.layout.main_layout);
    if (text == null)       text       = (TextView)     findViewById(R.id.text);
    if (layoutMain == null) layoutMain = (LinearLayout) findViewById(R.id.layout_main);

    // Sensors
    mSensorManager = (SensorManager) getSystemService(Context.SENSOR_SERVICE);
    if (mSensorManager.getDefaultSensor(Sensor.TYPE_GRAVITY) != null){
      List<Sensor> gravSensors = mSensorManager.getSensorList(Sensor.TYPE_GRAVITY);
      int nSensors = gravSensors.size();
      text.setText("Detected gravity sensors: " + Integer.toString(nSensors));

      for (int i = 0; i < nSensors; i++) {
        final TextView tvSensor = new TextView(this);
        final int      j        = i + 1;

        tvSensor.setLayoutParams(new LayoutParams(LayoutParams.WRAP_CONTENT, LayoutParams.WRAP_CONTENT));

        mSensor = gravSensors.get(i);
        mSensorManager.registerListener(new SensorEventListener() {
          @Override
          public void onSensorChanged(final SensorEvent event) {
    		    float x = event.values[0];
    		    float y = event.values[1];
    		    float z = event.values[2];
    		    float g = (float) sqrt(x*x + y*y + z*z);

            tvSensor.setText(String.format("Sensor %d: %f m/s^2", j, g));
          }

          @Override
          public void onAccuracyChanged(Sensor sensor, int a) {}
        }, mSensor, SensorManager.SENSOR_DELAY_NORMAL);

        layoutMain.addView(tvSensor);
      }
    }
    else {
      text.setText("We DO NOT have gravity! :(");a
    }
  }

}
{% endhighlight %}

The code is fairly simple and quite self-explanatory. We override the `onCreate` method of the `Activity` class, from which `MainActivity` inherits, to set up the UI. We use a layout resource as a basis, which we then dynamically extend with extra `TextView` widgets to hold the value of each gravity sensor that gets discovered at run-time.

## The Layout Resource

In this project we have a mixture of static layout resources and dynamic creation of `TextView` elements. This offers us the chance to see how to make resources available to the Java code, i.e. by placing them in the place where Gradle, and the Android Gradle plugin, would expect them. Files placed in the `src/main/res` folder are treated as resources and can be referenced in the way described at the Android Developer portal. In the previous code block, on line 36 we have

{% highlight java%}
    setContentView(R.layout.main_layout);
{% endhighlight %}

The expression `R.layout.main_layout` refers to the resource `main_layout.xml` located in the `layout` sub-folder of `src/main/res`. The various grouping of resources is detailed at the page [Providing Resources](https://developer.android.com/guide/topics/resources/providing-resources.html).

Later on, in dealing with the output of the `lint` task, we will have the chance to look at the `strings.xml` resources in the `values` sub-folder. For the time being, let's have a look at what the `main_layout.xml` looks like in this case:

{% highlight xml %}
<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
              android:id="@+id/layout_main"
              android:layout_width="match_parent"
              android:layout_height="match_parent"
              android:padding="32px"
              android:gravity="center"
              android:orientation="vertical" >

  <TextView android:id="@+id/text"
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:paddingBottom="12px"
            android:text="Gravity sensors" />

  <!--
  A new TextView element will be added programmatically for each on-board
  gravity sensor detected.
  -->

</LinearLayout>
{% endhighlight %}

This is a rather simple layout. We create a vertical `LinearLayout` container to display a vertical stack of `TextView` elements. The first one, statically included in the XML resource file, will hold the counter of the discovered gravity sensors. More `TextView` elements are added at run-time, one for each of the sensors, to display their updated value.


# Running the Application

Now that we have set up the Gradle project and coded our application, it is time to build it and install it on an Android device to run it. In this section we shall see how to invoke the Gradle `build` task to generate the APK (the Android Package Kit) package, and how to install it on our devices, being them either virtual or physical, in two different ways. Finally, we will give a final touch to our sample application by fixing a few of the issue reported by the `lint` task.

## Building with Gradle

The process of building an Android application involves many steps and tools. If we rely on a Gradle project, as we have done in this case, and as it would be if you were using Android Studio, all of the details of this process are hidden to us. In a post where we are trying to make use of only simple tools, you may think that Gradle would defeat the point. Whilst I'd agree with you, I also believe that we will have to draw a line at some point, and Gradle feels like the right place. If, at any point, you feel the need to manually build your project, you can refer to these two references for more details:

- [Building Android Application Bundles (APKs) by Hand](https://spin.atomicobject.com/2011/08/22/building-android-application-bundles-apks-by-hand/)
- [Jack, Jill & building Android apps by hand](http://czak.pl/2016/05/31/handbuilt-android-project.html)

This being said, let's see how to build our sample project with Gradle. We can list all the available tasks with

{% terminal $ %}
./gradlew tasks --all
{% endterminal %}

Among all the tasks listed by the previous command, we should see the following ones

{% terminal %}
Build tasks
-----------
assemble - Assembles all variants of all applications and secondary packages.
assembleAndroidTest - Assembles all the Test applications.
assembleDebug - Assembles all Debug builds.
assembleRelease - Assembles all Release builds.
build - Assembles and tests this project.
buildDependents - Assembles and tests this project and all projects that depend on it.
buildNeeded - Assembles and tests this project and all projects it depends on.
clean - Deletes the build directory.
cleanBuildCache - Deletes the build cache directory.
compileDebugAndroidTestSources
compileDebugSources
compileDebugUnitTestSources
compileReleaseSources
compileReleaseUnitTestSources
mockableAndroidJar - Creates a version of android.jar that's suitable for unit tests.
{% endterminal %}

We could decide to `assemble` our project, or `build` it in case we also wrote tests and want them built too. As it doesn't make much of a difference in our case, we can run the `build` task with

{% terminal $ %}
./gradlew build
{% endterminal %}

> The `build` task actually does a bit more than assemble and execute tests. It also runs the `lint` task. More on this later.

If the build task was successful, you should now have the `androtest-debug.apk` into the `build/outputs/apk` folder, ready to be deployed on an Android device.


## Creating a Virtual Device

In case you want to install the application on a physical device, you can skip this section and go straight to the next one. Under some circumstances, you might want to test your application on diverse hardware settings, and the best way is probably to make use of a _virtual device_. If you have installed the `emulator` package as previously described, you can create a virtual machine with the following commands. But first we need to install a _system image_, for example the **Intel x86 Atom_64 System Image**. Since our application doesn't make use of the Google APIs we can opt for the default image:

{% terminal $ %}
sdkmanager "system-images;android-23;default;x86_64"
{% endterminal %}

The download and installation might take some time, so just wait for `sdkmanager` to complete. You can then proceed to creating a virtual device with

{% terminal $ %}
avdmanager create avd -n test -k "system-images;android-23;default;x86_64" -d 8
{% endterminal %}

This will create a virtual device named `test` with the system image that we have just downloaded. The `-d` switch specifies which device we want to emulate. In this case the value 8 represents a "Nexus 5" device. A complete list of the devices that can be emulated may be found with

{% terminal $ %}
avdmanager list device
{% endterminal %}

Finally, to run the newly created virtual device we use the `emulator` tool, just like this:

{% terminal $ %}
emulator @test -skin 768x1280
{% endterminal %}

where `@test` specified the name of the virtual device we want to run, and the `-skin` switch defines the resolution we want to run the emulator at. Note that a bug in the `emulator` tools prevents you from running this command from any working directory. Instead, you need to navigate to `$ANDROID_HOME/emulator` in order to start it without errors.

For more details on how to manage virtual devices, have a look at the [`avdmanager`](https://developer.android.com/studio/command-line/avdmanager.html#global_options) documentation page.

## Installing the APK

There are at least to ways of installing the APK to an Android device. One is via a Gradle task, and the other is more manual and involves the Android Debug Bridge tool `adb`. Let's have a look at both.

From the previous run of the `./gradlew tasks --all`, you should have seen the following tasks

{% terminal %}
Install tasks
-------------
installDebug - Installs the Debug build.
installDebugAndroidTest - Installs the android (on device) tests for the Debug build.
uninstallAll - Uninstall all applications.
uninstallDebug - Uninstalls the Debug build.
uninstallDebugAndroidTest - Uninstalls the android (on device) tests for the Debug build.
uninstallRelease - Uninstalls the Release build.
{% endterminal %}

The `installDebug` task will look for all the Android devices in debugging mode connected to your machine and attempt to install the APK on _all_ of them. For instance, if you have a physical device in debug mode connected to your PC/laptop while also running a virtual device, this Gradle task will install the APK on both of them.

If you want to install the APK on only one of the currently connected devices, you can do so with the `adb` tool. First of all, determine the identifier of each of the connected devices with

{% terminal %}
$ adb devices
List of devices attached
* daemon not running. starting it now at tcp:5037 *
* daemon started successfully *
05426e2409d30434	device
emulator-5554	device
{% endterminal %}

The device with ID `05426e2409d30434` is a physical Nexus 5 in debug mode connected via USB to my laptop, while `emulator-5554`, as the name indicates, is a running instance of the `test` virtual device we created before. We can install the APK on e.g. the emulator with

{% terminal $ %}
adb -s "emulator-5554" install build/outputs/apk/androtest-debug.apk
{% endterminal %}

which will now be ready to be executed on the virtual device.

## The lint tasks

If you have ever used Android Studio you might wonder if there is the chance to get all the useful code analysis and hints that the IDE brings up while you code your application. While this feature is probably not supported by the text editor of your choice, we can remedy by using the lint tool provided by the Android SDK. A convenient way to invoke it is through a dedicated Gradle task. From the output of `./gradlew tasks --all` you should also see the following tasks

{% terminal %}
Verification tasks
------------------
check - Runs all checks.
connectedAndroidTest - Installs and runs instrumentation tests for all flavors on connected devices.
connectedCheck - Runs all device checks on currently connected devices.
connectedDebugAndroidTest - Installs and runs the tests for debug on connected devices.
deviceAndroidTest - Installs and runs instrumentation tests using all Device Providers.
deviceCheck - Runs all device checks using Device Providers and Test Servers.
lint - Runs lint on all variants.
lintDebug - Runs lint on the Debug build.
lintRelease - Runs lint on the Release build.
test - Run unit tests for all variants.
testDebugUnitTest - Run unit tests for the debug build.
testReleaseUnitTest - Run unit tests for the release build.
{% endterminal %}

Notice how we can invoke the lint tool in multiple ways. As we saw before, the `build` task, as opposed to `assemble`, will also run the lint tool. But we can also choose to run it as part of a full check with the `check` task, or just on its own, on every variant of our project or simply on the debug build. As an example, let's run the `lint` task with

{% terminal $ %}
./gradlew lint
{% endterminal %}

The output should contain something that looks like the following

{% terminal %}
...
> Task :lint
Ran lint on variant debug: 13 issues found
Ran lint on variant release: 13 issues found
Wrote HTML report to file:///home/gabriele/Projects/androtest/build/reports/lint-results.html
Wrote XML report to file:///home/gabriele/Projects/androtest/build/reports/lint-results.xml


BUILD SUCCESSFUL in 1s
25 actionable tasks: 7 executed, 18 up-to-date
{% endterminal %}

This tells us that the lint tool has found 13 issues on both the debug and the release build of our project, and that a report is available as both an HTML and an XML file in `build/reports`.

Let's open the HTML report and have a look at the reported issues. As predictable, the largest number of issues is about _internationalisation_, as we have used many hard-coded strings in our source code. So let's try to fix some of these, starting from the `HardcodedText` one. By clicking on it, we get sent to a more detailed part of the page that suggests us to use a `@string` resource instead of the hard-coded string `Gravity sensors`. Since our code will change the string at run-time in any case, the simplest solution is to replace it with an empty string. If we now run the lint task again, we should see only 12 issues. Good! :).

Let's now tackle a couple of _TextView Internationalization_ issues. The first one is about the string `"Detected gravity sensors: " + Integer.toString(nSensors)` that we have used in the `MainActivity.java` source file. The problem here is two-fold. We should use a resource string and favour placeholders rather than concatenation. So let's create a [string resource](https://developer.android.com/guide/topics/resources/string-resource.html) file. Recall from before that this should go in an XML file, say `strings.xml`, within the `src/main/res/values` folder.

{% highlight html %}
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="sensors_no">Detected gravity sensors: %d</string>
</resources>
{% endhighlight %}

We can now replace line 44 in `MainActivity.java` with

{% highlight java %}
      text.setText(getString(R.string.sensors_no, nSensors));
{% endhighlight %}

Run the lint task again, and the count should now be down to only 9 issues. This should give you the idea of how to continue fixing the remaining findings.


# Conclusions

In this post we saw that, if we want to develop Android applications by simply relying on a text editor and some command line tools, the initial set up of the development environment requires a few preliminary steps, some of which are performed when you install Android Studio. However, some of the other steps need to be performed regardless, with the only difference that, in Android Studio, you would have a GUI to assist you. The bonus of going IDE-free, however, is in the fact that we now know what operations are being performed by the IDE when, e.g., we install an Android SDK that targets a certain API level.

Creating a Gradle project is quite easy, and in this we are assisted by Gradle itself. The Android Gradle plugin takes care of invoking the right tools to perform the most common tasks, like building our project, or even installing it on an Android device. One handy feature that we might miss out with a plain text editor is the live linting of our code. However, at any stage of the development, we can run the `lint` Gradle task to generate a report with all the issues that have been discovered within the whole project.

This post should have also showed you that, whilst Android Studio is a very useful tool, there is practically nothing that we would miss out by using the command line tools of the SDK instead. Development might at first be less smooth, and the learning curve steeper, but surely has its positives too.
